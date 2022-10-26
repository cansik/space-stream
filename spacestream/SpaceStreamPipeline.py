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
from duit.model.DataField import DataField
import duit.ui as dui

from spacestream.codec.DepthCodec import DepthCodec
from spacestream.codec.DepthCodecType import DepthCodecType
from spacestream.codec.InverseHueColorization import InverseHueColorization
from spacestream.codec.RealSenseColorizer import RealSenseColorizer
from spacestream.fbs import FrameBufferSharingServer
from spacestream.io.EnhancedJSONEncoder import EnhancedJSONEncoder
from spacestream.io.StreamInformation import StreamInformation, StreamSize, Vector2, RangeValue


def linear_interpolate(x):
    return x


def ease_out_quad(x):
    # decode = sqrt(x)
    return x * (2 - x)


class SpaceStreamPipeline(vg.BaseGraph):

    def __init__(self, stream_name: str, input: vg.BaseInput, fbs_client: FrameBufferSharingServer,
                 codec: DepthCodecType = DepthCodecType.UniformHue,
                 min_distance: float = 0, max_distance: float = 6,
                 record: bool = False, masking: bool = False,
                 segnet: Optional[vg.InstanceSegmentationEstimator] = None, use_midas: bool = False,
                 multi_threaded: bool = False, handle_signals: bool = True):
        super().__init__(multi_threaded, False, handle_signals)

        self.stream_name = stream_name
        self.input = input
        self.fbs_client = fbs_client
        self.fps_tracer = vg.FPSTracer()

        self.depth_units: float = 0.001

        self._intrinsic_update_requested = True

        # options
        self.pipeline_fps = DataField("-") | dui.Text("Pipeline FPS", readonly=True)
        self.encoding_time = DataField("-") | dui.Text("Encoding Time", readonly=True)
        self.disable_preview = DataField(False) | dui.Boolean("Disable Preview")
        self.record = DataField(record) | dui.Boolean("Record")

        self.serial_number = DataField("-")
        self.intrinsics_res = DataField("-")
        self.intrinsics_principle = DataField("-")
        self.intrinsics_focal = DataField("-")
        self.normalize_intrinsics = DataField(True)

        self.stream_information = StreamInformation()

        def _request_intrinsics_update(value: bool):
            self._intrinsic_update_requested = True

        if isinstance(input, vg.BaseDepthCamera):
            self.serial_number | dui.Text("Serial", readonly=True, copy_content=True)
            self.intrinsics_res | dui.Text("Resolution", readonly=True, copy_content=True)
            self.intrinsics_principle | dui.Text("Principle Point", readonly=True, copy_content=True)
            self.intrinsics_focal | dui.Text("Focal Point", readonly=True, copy_content=True)
            self.normalize_intrinsics | dui.Boolean("Normalize Intrinsics")
            self.normalize_intrinsics.on_changed += _request_intrinsics_update

        self.depth_codec: DepthCodec = codec.value()
        self.codec = DataField(codec) | dui.Enum("Codec")
        self.min_distance = DataField(float(min_distance)) | dui.Number("Min Distance")
        self.max_distance = DataField(float(max_distance)) | dui.Number("Max Distance")

        def codec_changed(c):
            self.depth_codec = c.value()

        self.codec.on_changed += codec_changed

        self.recorder: Optional[vg.VidGearVideoRecorder] = None
        self.crf: int = 23

        self.show_preview = True

        self.masking = masking
        self.segmentation_network: Optional[vg.InstanceSegmentationEstimator] = None

        if self.masking:
            self.segmentation_network = segnet
            if isinstance(self.segmentation_network, vg.MediaPipePoseEstimator):
                self.segmentation_network.enable_segmentation = True
            self.add_nodes(self.segmentation_network)

        self.use_midas = use_midas
        self.midas_net: Optional[vg.MidasDepthEstimator] = None

        if self.use_midas:
            self.midas_net = vg.MidasDepthEstimator.create(vg.MidasConfig.MidasSmall)
            self.midas_net.prediction_bit_depth = 16
            self.add_nodes(self.midas_net)

        # events
        self.on_frame_ready: Optional[Callable[[np.ndarray], None]] = None

        # time
        self.encoding_watch = vg.ProfileWatch()

        self.add_nodes(self.input)

    def _update_intrinsics(self, frame: np.ndarray) -> bool:
        h, w = frame.shape[:2]
        self.intrinsics_res.value = f"{w} x {h}"

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

            if self.normalize_intrinsics.value:
                ppx /= w
                ppy /= h
                fx /= w
                fy /= h

                pp_str = f"{ppx:.4f} / {ppy:.4f}"
                f_str = f"{fx:.4f} / {fy:.4f}"

            self.intrinsics_principle.value = pp_str
            self.intrinsics_focal.value = f_str

            self.stream_information.serial = self.input.serial
            self.stream_information.resolution = StreamSize(w, h)
            self.stream_information.intrinsics.principle = Vector2(ppx, ppy)
            self.stream_information.intrinsics.focal = Vector2(fx, fy)
            self.stream_information.distance = RangeValue(self.min_distance.value, self.max_distance.value)
        else:
            self.intrinsics_principle.value = "-"
            self.intrinsics_focal.value = "-"

        return True

    def _init(self):
        super()._init()

        if threading.current_thread() is threading.main_thread():
            self.fbs_client.setup()

        if isinstance(self.input, vg.BaseDepthCamera):
            self.serial_number.value = self.input.serial
            logging.info(f"Device Serial: {self.input.serial}")

        # set colorizer min and max settings
        if isinstance(self.input, vg.RealSenseInput):
            if not self.use_midas:
                self.input.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)
                self.input.colorizer.set_option(rs.option.min_distance, self.min_distance.value)
                self.input.colorizer.set_option(rs.option.max_distance, self.max_distance.value)

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
        if self.record.value and self.recorder is None:
            time_str = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
            output_file_path = f"recordings/{self.stream_name}-{time_str}.mp4"
            self.recorder = vg.VidGearVideoRecorder(output_file_path, fps=self.input.fps)
            self.recorder.output_params.update({
                "-crf": self.crf,
                "-input_framerate": round(self.fps_tracer.smooth_fps)
            })
            self.recorder.open()

            # write recording parameters
            with open(Path(output_file_path).with_suffix(".json"), "w") as f:
                json.dump(self.stream_information, f, cls=EnhancedJSONEncoder, indent=4)
        elif not self.record.value and self.recorder is not None:
            self.recorder.close()
            self.recorder = None

        if self.masking:
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
            if isinstance(self.depth_codec, InverseHueColorization) and self.min_distance.value <= 0.0:
                logging.warning("Inverse Hue Colorization needs min-range to be higher than 0.0")
                self.min_distance.value = 0.1

            if self.min_distance.value < 0.0:
                self.min_distance.value = 0.0

            if self.max_distance.value == 0.0:
                self.max_distance.value = 0.1

            if self.min_distance.value >= self.max_distance.value:
                self.min_distance.value = self.max_distance.value - 0.1

            # read depth map and create rgb-d image
            min_value = round(self.min_distance.value / self.depth_units)
            max_value = round(self.max_distance.value / self.depth_units)

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

            if self.masking:
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

        if self.record and self.recorder is not None:
            self.recorder.add_image(rgbd)

        if not self.disable_preview.value and self.on_frame_ready is not None:
            self.on_frame_ready(rgbd)
        else:
            bgrd = cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR)
            self.fbs_client.send(bgrd)

        self.fps_tracer.update()
        self.pipeline_fps.value = f"{self.fps_tracer.fps:.2f}"

        self.encoding_time.value = f"{self.encoding_watch.average():.2f} ms"

    def _release(self):
        if threading.current_thread() is threading.main_thread():
            self.fbs_client.release()

        super()._release()
        if self.record.value and self.recorder is not None:
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
