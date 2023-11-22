import argparse
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, List

import cv2
import numpy as np
import pyrealsense2 as rs
import visiongraph as vg

from spacestream.SpaceStreamConfig import SpaceStreamConfig
from spacestream.codec.DepthCodec import DepthCodec
from spacestream.codec.InverseHueColorization import InverseHueColorization
from spacestream.codec.RealSenseColorizer import RealSenseColorizer
from spacestream.fbs.FrameBufferSharingServer import FrameBufferSharingServer
from spacestream.io.EnhancedJSONEncoder import EnhancedJSONEncoder
from spacestream.io.StreamInformation import StreamInformation, StreamSize, Vector2, RangeValue


def linear_interpolate(x):
    return x


def ease_out_quad(x):
    # decode = sqrt(x)
    return x * (2 - x)


class SpaceStreamGraph(vg.VisionGraph):

    def __init__(self, config: SpaceStreamConfig,
                 input_node: vg.BaseInput,
                 segnet: Optional[vg.InstanceSegmentationEstimator] = None,
                 multi_threaded: bool = False, daemon: bool = True, handle_signals: bool = True):
        super().__init__(input_node,
                         name=f"SpaceStream",
                         multi_threaded=multi_threaded,
                         daemon=daemon,
                         handle_signals=handle_signals)

        self.config = config

        self.input = input_node
        self.fps_tracer = vg.FPSTracer()
        self.fbs_client = FrameBufferSharingServer.create(config.stream_name.value)

        def on_stream_name_changed(new_stream_name: str):
            logging.info("changing stream name...")
            self.fbs_client.release()
            self.fbs_client = FrameBufferSharingServer.create(new_stream_name)
            self.fbs_client.setup()
            logging.info(f"stream name changed to {new_stream_name}")

        self.config.stream_name.on_changed += on_stream_name_changed

        self.depth_units: float = 0.001

        self._intrinsic_update_requested = True

        self.stream_information = StreamInformation()

        def _request_intrinsics_update(value: bool):
            self._intrinsic_update_requested = True

        self.config.normalize_intrinsics.on_changed += _request_intrinsics_update
        self.depth_codec: DepthCodec = self.config.codec.value.value()

        def codec_changed(c):
            self.depth_codec = c.value()

        self.config.codec.on_changed += codec_changed

        self.recorder: Optional[vg.VidGearVideoRecorder] = None
        self.crf: int = 23

        self.show_preview = True
        self.segmentation_network: Optional[vg.InstanceSegmentationEstimator] = None

        if self.config.masking.value:
            self.segmentation_network = segnet
            if isinstance(self.segmentation_network, vg.MediaPipePoseEstimator):
                self.segmentation_network.enable_segmentation = True
            self.add_nodes(self.segmentation_network)

        # todo: enable midas again - currently it is disabled
        self.use_midas = False
        self.midas_net: Optional[vg.MidasDepthEstimator] = None

        if self.use_midas:
            self.midas_net = vg.MidasDepthEstimator.create(vg.MidasConfig.MidasSmall)
            self.midas_net.prediction_bit_depth = 16
            self.add_nodes(self.midas_net)

        # events
        self.on_frame_ready: Optional[Callable[[np.ndarray], None]] = None

        # time
        self.encoding_watch = vg.ProfileWatch()

        self.add_nodes(self.fbs_client)

    def _update_intrinsics(self, frame: np.ndarray) -> bool:
        h, w = frame.shape[:2]
        self.config.intrinsics_res.value = f"{w} x {h}"

        if isinstance(self.input, vg.BaseDepthCamera):
            try:
                intrinsics = self.input.camera_matrix
            except Exception as ex:
                print(f"Intrinsics could not be read: {ex}")
                return False

            ppx = intrinsics[0, 2]
            ppy = intrinsics[1, 2]

            fx = intrinsics[0, 0]
            fy = intrinsics[1, 1]

            pp_str = f"{ppx:.2f} / {ppy:.2f}"
            f_str = f"{fx:.2f} / {fy:.2f}"

            if self.config.normalize_intrinsics.value:
                ppx /= w
                ppy /= h
                fx /= w
                fy /= h

                pp_str = f"{ppx:.4f} / {ppy:.4f}"
                f_str = f"{fx:.4f} / {fy:.4f}"

            self.config.intrinsics_principle.value = pp_str
            self.config.intrinsics_focal.value = f_str

            self.stream_information.serial = self.input.serial
            self.stream_information.resolution = StreamSize(w, h)
            self.stream_information.intrinsics.principle = Vector2(ppx, ppy)
            self.stream_information.intrinsics.focal = Vector2(fx, fy)
            self.stream_information.distance = RangeValue(self.config.min_distance.value, self.config.max_distance.value)
        else:
            self.config.intrinsics_principle.value = "-"
            self.config.intrinsics_focal.value = "-"

        return True

    def _init(self):
        super()._init()

        if threading.current_thread() is threading.main_thread():
            self.fbs_client.setup()

        if isinstance(self.input, vg.BaseDepthCamera):
            self.config.serial_number.value = self.input.serial
            logging.info(f"Device Serial: {self.input.serial}")

        # set colorizer min and max settings
        if isinstance(self.input, vg.RealSenseInput):
            if not self.use_midas:
                self.input.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)
                self.input.colorizer.set_option(rs.option.min_distance, self.config.min_distance.value)
                self.input.colorizer.set_option(rs.option.max_distance, self.config.max_distance.value)

        if isinstance(self.input, vg.AzureKinectInput):
            from pyk4a import CalibrationType

            calibration = self.input.device.calibration
            mat = calibration.get_camera_matrix(CalibrationType.DEPTH)
            print(mat)

    def _process(self):
        ts, frame = self.input.read()

        if frame is None:
            return

        # start recording
        if self.config.record.value and self.recorder is None:
            time_str = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
            output_file_path = f"recordings/{self.config.stream_name}-{time_str}.mp4"
            self.recorder = vg.VidGearVideoRecorder(output_file_path, fps=self.input.fps)
            self.recorder.output_params.update({
                "-crf": self.crf,
                "-input_framerate": round(self.fps_tracer.smooth_fps)
            })
            self.recorder.open()

            # write recording parameters
            with open(Path(output_file_path).with_suffix(".json"), "w") as f:
                json.dump(self.stream_information, f, cls=EnhancedJSONEncoder, indent=4)
        elif not self.config.record.value and self.recorder is not None:
            self.recorder.close()
            self.recorder = None

        if self.config.masking.value:
            segmentations: List[vg.InstanceSegmentationResult] = self.segmentation_network.process(frame)
            for segment in segmentations:
                frame = self.mask_image(frame, segment.mask)

        if isinstance(self.input, vg.BaseDepthInput):
            if isinstance(self.input, vg.RealSenseInput):
                self.depth_units = self.input.depth_frame.get_units()

            if self.midas_net is not None:
                depth_buffer = self.midas_net.process(frame)
            else:
                depth_buffer = self.input

            depth = depth_buffer.depth_buffer

            if self.use_midas:
                depth = pow(2, 16) - depth

            # check pre-conditions (move them to the changing side)
            if isinstance(self.depth_codec, InverseHueColorization) and self.config.min_distance.value <= 0.0:
                logging.warning("Inverse Hue Colorization needs min-range to be higher than 0.0")
                self.config.min_distance.value = 0.1

            if self.config.min_distance.value < 0.0:
                self.config.min_distance.value = 0.0

            if self.config.max_distance.value == 0.0:
                self.config.max_distance.value = 0.1

            if self.config.min_distance.value >= self.config.max_distance.value:
                self.config.min_distance.value = self.config.max_distance.value - 0.1

            # read depth map and create rgb-d image
            min_value = round(self.config.min_distance.value / self.depth_units)
            max_value = round(self.config.max_distance.value / self.depth_units)

            self.encoding_watch.start()
            if isinstance(self.input, vg.RealSenseInput) and isinstance(self.depth_codec, RealSenseColorizer):
                depth_map = self.depth_codec.encode(self.input.depth_frame, min_value, max_value)
            else:
                depth_map = self.depth_codec.encode(depth, min_value, max_value)
            self.encoding_watch.stop()

            # fix realsense image if it has been aligned to remove lines
            if isinstance(self.input, vg.RealSenseInput):
                depth_map = cv2.medianBlur(depth_map, 3)

            # resize to match rgb image if necessary
            if depth_map.shape != frame.shape:
                h, w = frame.shape[:2]
                depth_map = cv2.resize(depth_map, (w, h), interpolation=cv2.INTER_AREA)

            if self.config.masking.value:
                for segment in segmentations:
                    depth_map = self.mask_image(depth_map, segment.mask)

            rgbd = np.hstack((depth_map, frame))
        else:
            # just send rgb image for testing
            rgbd = frame

        if self._intrinsic_update_requested:
            success = self._update_intrinsics(frame)
            self._intrinsic_update_requested = not success

        if threading.current_thread() is threading.main_thread():
            # send rgb-d over spout
            bgrd = cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR)
            self.fbs_client.send(bgrd)

        if self.config.record.value and self.recorder is not None:
            self.recorder.add_image(rgbd)

        if not self.config.disable_preview.value and self.on_frame_ready is not None:
            self.on_frame_ready(rgbd)
        else:
            bgrd = cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR)
            self.fbs_client.send(bgrd)

        self.fps_tracer.update()
        self.config.pipeline_fps.value = f"{self.fps_tracer.fps:.2f}"

        self.config.encoding_time.value = f"{self.encoding_watch.average():.2f} ms"

    def _release(self):
        if threading.current_thread() is threading.main_thread():
            self.fbs_client.release()

        super()._release()
        if self.config.record.value and self.recorder is not None:
            self.recorder.close()

    @staticmethod
    def mask_image(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        masked = cv2.bitwise_and(image, image, mask=mask)
        return masked

    @staticmethod
    def add_params(parser: argparse.ArgumentParser):
        pass

    def configure(self, args: argparse.Namespace):
        super().configure(args)

        self.crf = args.record_crf
