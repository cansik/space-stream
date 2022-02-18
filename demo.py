import argparse
import logging
import threading
from datetime import datetime
from enum import Enum
from functools import partial
from typing import Callable, Optional, List

import configargparse
import cv2
import numpy as np
import pyrealsense2 as rs
import visiongraph as vg
from visiongraph.input import add_input_step_choices

from fbs.FrameBufferSharingServer import FrameBufferSharingServer


class DepthEncoding(Enum):
    Colorizer = 1,
    Linear = 2,
    Quad = 3,


def linear_interpolate(x):
    return x


def ease_out_quad(x):
    # decode = sqrt(x)
    return x * (2 - x)


segmentation_networks = {
    "mediapipe": partial(vg.MediaPipePoseEstimator.create, vg.PoseModelComplexity.Normal),
    "mediapipe-light": partial(vg.MediaPipePoseEstimator.create, vg.PoseModelComplexity.Light),
    "mediapipe-heavy": partial(vg.MediaPipePoseEstimator.create, vg.PoseModelComplexity.Heavy),

    "maskrcnn": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_608_FP32),
    "maskrcnn-eff-480": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_480_FP16),
    "maskrcnn-eff-608": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_608_FP16),
    "maskrcnn-res50-768": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.ResNet50_1024x768_FP16),
    "maskrcnn-res101-800": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.ResNet101_1344x800_FP16)
}


class DemoPipeline(vg.BaseGraph):

    def __init__(self, stream_name: str, input: vg.BaseInput, fbs_client: FrameBufferSharingServer,
                 encoding: DepthEncoding = DepthEncoding.Colorizer,
                 min_distance: float = 0, max_distance: float = 6, bit_depth: int = 8,
                 record: bool = False, masking: bool = False,
                 segnet: Optional[vg.InstanceSegmentationEstimator] = None, use_midas: bool = False):
        super().__init__(False, False, handle_signals=True)

        self.stream_name = stream_name
        self.input = input
        self.fbs_client = fbs_client
        self.fps_tracer = vg.FPSTracer()

        self.depth_units: float = 0.001

        self.encoding = encoding
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.bit_depth = bit_depth

        self.record = record
        self.recorder: Optional[vg.CV2VideoRecorder] = None

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
            self.add_nodes(self.midas_net)

        self.add_nodes(self.input, self.fbs_client)

    def _init(self):
        super()._init()

        # set colorizer min and max settings
        if isinstance(self.input, vg.RealSenseInput):
            self.input.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)
            self.input.colorizer.set_option(rs.option.min_distance, self.min_distance)
            self.input.colorizer.set_option(rs.option.max_distance, self.max_distance)

            # display intrinsics
            profiles = self.input.pipeline.get_active_profile()

            stream = profiles.get_stream(rs.stream.depth).as_video_stream_profile()
            intrinsics = stream.get_intrinsics()
            logging.info(f"Depth Intrinsics: {intrinsics}")

            stream = profiles.get_stream(rs.stream.color).as_video_stream_profile()
            intrinsics = stream.get_intrinsics()
            logging.info(f"RGB Intrinsics: {intrinsics}")

        if isinstance(self.input, vg.AzureKinectInput):
            from pyk4a import CalibrationType

            calibration = self.input.device.calibration
            mat = calibration.get_camera_matrix(CalibrationType.DEPTH)

            logging.info(f"Serial: {self.input.device.serial}")
            logging.info(f"Depth Intrinsics:\n{mat}")

    def _process(self):
        ts, frame = self.input.read()

        if frame is None:
            return

        # start recording
        if self.record and self.recorder is None:
            h, w = frame.shape[:2]
            rw = w * 2
            rh = h
            time_str = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
            output_file_path = f"recordings/{self.stream_name}-{time_str}.mp4"
            self.recorder = vg.CV2VideoRecorder(rw, rh, output_file_path, fps=self.input.fps)
            self.recorder.open()

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

            # read depth map and create rgb-d
            if self.encoding == DepthEncoding.Colorizer:
                depth_map = self.input.depth_map
            elif self.encoding == DepthEncoding.Linear:
                depth_map = self.encode_depth_information(depth, linear_interpolate, self.bit_depth)
            elif self.encoding == DepthEncoding.Quad:
                depth_map = self.encode_depth_information(depth, ease_out_quad, self.bit_depth)
            else:
                raise Exception("No encoding method is set!")

            # resize to match rgb image if necessary
            if depth_map.shape != frame.shape:
                h, w = frame.shape[:2]
                depth_map = cv2.resize(depth_map, (w, h))

            if self.masking:
                for segment in segmentations:
                    depth_map = self.mask_image(depth_map, segment.mask)

            rgbd = np.hstack((depth_map, frame))
        else:
            # just send rgb image for testing
            rgbd = frame

        # send rgb-d over spout
        bgrd = cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR)
        self.fbs_client.send(bgrd)

        if self.record and self.recorder is not None:
            self.recorder.add_image(bgrd)

        self.fps_tracer.update()

        # imshow does only work in main thread!
        if self.show_preview and threading.current_thread() is threading.main_thread():
            cv2.putText(rgbd, "FPS: %.0f" % self.fps_tracer.smooth_fps,
                        (7, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1, cv2.LINE_AA)

            cv2.imshow(f"RGB-D FrameBuffer Sharing Demo ({self.stream_name})", rgbd)
            key_code = cv2.waitKey(15) & 0xFF
            if key_code == 27:
                self.close()

            key = chr(key_code).lower()
            if key == "h":
                print("Help:")
                print("\tUse numbers to toggle through encodings (example: Colorizer = 0, Linear = 1, ...)")
                print("\tUse 'b' to change the bit-depth")
                print("\tUse 'esq' to close the application")

            if key == "b":
                if self.bit_depth == 8:
                    self.bit_depth = 16
                else:
                    self.bit_depth = 8
                print(f"Switched bit-depth to {self.bit_depth} bits.")

            if key.isnumeric():
                index = int(key)
                encodings = list({item.name: item for item in list(DepthEncoding)}.values())

                if index < len(encodings):
                    self.encoding = encodings[index]
                    print(f"Switch to {self.encoding} ({index})")

    def _release(self):
        super()._release()
        if self.record and self.recorder is not None:
            self.recorder.close()

    def encode_depth_information(self, depth: np.ndarray,
                                 interpolation: Callable,
                                 bit_depth: int) -> np.ndarray:
        # prepare information
        min_value = round(self.min_distance / self.depth_units)
        max_value = round(self.max_distance / self.depth_units)
        d_value = max_value - min_value
        total_unique_values = pow(2, bit_depth) - 1

        # read depth, clip, normalize and map
        depth[depth == 0] = max_value  # set 0 (no-data points) to max value
        depth = np.clip(depth, min_value, max_value)
        depth = (depth - min_value) / d_value  # normalize

        depth = interpolation(depth)
        depth = 1.0 - depth  # flip

        # convert to new bit range
        depth = (depth * total_unique_values).astype(np.uint16)

        # map to RGB image (8 or 16 bit)
        if bit_depth == 8:
            return cv2.cvtColor(depth.astype(np.uint8), cv2.COLOR_GRAY2RGB)

        # bit depth 16 bit
        out = np.expand_dims(depth, axis=2)

        r_channel = out * 0
        g_channel = (out >> 8) & 0xff
        b_channel = out & 0xff

        out = np.concatenate((b_channel, g_channel, r_channel), axis=2)
        return out.astype(np.uint8)

    @staticmethod
    def mask_image(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        masked = cv2.bitwise_and(image, image, mask=mask)
        return masked

    @staticmethod
    def add_params(parser: argparse.ArgumentParser):
        pass

    def configure(self, args: argparse.Namespace):
        super().configure(args)

        self.show_preview = not args.no_preview


if __name__ == "__main__":
    parser = configargparse.ArgumentParser(description="RGB-D framebuffer sharing demo for visiongraph")
    parser.add_argument("-c", "--config", required=False, is_config_file=True, help="Configuration file path.")
    vg.add_logging_parameter(parser)
    vg.add_enum_choice_argument(parser, DepthEncoding, "--depth-encoding",
                                help="Method how the depth map will be encoded")
    parser.add_argument("--min-distance", type=float, default=0, help="Min distance to perceive by the camera.")
    parser.add_argument("--max-distance", type=float, default=6, help="Max distance to perceive by the camera.")
    parser.add_argument("--bit-depth", type=int, default=8, choices=[8, 16],
                        help="Encoding output bit depth (default: 8).")
    parser.add_argument("--stream-name", type=str, default="RGBDStream", help="Spout / Syphon stream name.")

    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)
    input_group.add_argument("--midas", action="store_true", help="Use midas for depth capture.")

    masking_group = parser.add_argument_group("masking")
    masking_group.add_argument("--mask", action="store_true", help="Apply mask by segmentation algorithm.")
    vg.add_step_choice_argument(parser, segmentation_networks, name="--segnet", default="mediapipe",
                                help="Segmentation Network", add_params=False)

    debug_group = parser.add_argument_group("debug")
    debug_group.add_argument("--no-filter", action="store_true", help="Disable realsense image filter.")
    debug_group.add_argument("--no-preview", action="store_true", help="Disable preview to speed.")
    debug_group.add_argument("--record", action="store_true", help="Record output into recordings folder.")

    args = parser.parse_args()

    vg.setup_logging(args.loglevel)

    if issubclass(args.input, vg.BaseDepthInput):
        args.depth = True

    if issubclass(args.input, vg.RealSenseInput):
        logging.info("setting realsense options")
        args.depth = True
        args.color_scheme = vg.RealSenseColorScheme.WhiteToBlack

        if not args.no_filter:
            args.rs_filter = [rs.spatial_filter, rs.temporal_filter]

    if issubclass(args.input, vg.AzureKinectInput):
        args.k4a_align = True

    # create frame buffer sharing client
    fbs_client = FrameBufferSharingServer.create(args.stream_name)

    # run pipeline
    pipeline = DemoPipeline(args.stream_name, args.input(), fbs_client, args.depth_encoding,
                            args.min_distance, args.max_distance, args.bit_depth,
                            args.record, args.mask, args.segnet(), args.midas)
    pipeline.configure(args)
    pipeline.open()
