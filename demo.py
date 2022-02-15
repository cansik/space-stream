import argparse
import logging
import threading
from enum import Enum
from typing import Callable

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


class DemoPipeline(vg.BaseGraph):

    def __init__(self, input: vg.BaseInput, fbs_client: FrameBufferSharingServer,
                 encoding: DepthEncoding = DepthEncoding.Colorizer,
                 min_distance: float = 0, max_distance: float = 6, bit_depth: int = 8):
        super().__init__(False, False, handle_signals=True)

        self.input = input
        self.fbs_client = fbs_client
        self.fps_tracer = vg.FPSTracer()

        self.depth_units: float = 0.001

        self.encoding = encoding
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.bit_depth = bit_depth

        self.add_nodes(self.input, self.fbs_client)

    def _init(self):
        super()._init()

        # set colorizer min and max settings
        if isinstance(self.input, vg.RealSenseInput):
            self.input.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)
            self.input.colorizer.set_option(rs.option.min_distance, self.min_distance)
            self.input.colorizer.set_option(rs.option.max_distance, self.max_distance)

    def _process(self):
        ts, frame = self.input.read()

        if frame is None:
            return

        if isinstance(self.input, vg.BaseDepthInput):
            if isinstance(self.input, vg.RealSenseInput):
                self.depth_units = self.input.depth_frame.get_units()

            # read depth map and create rgb-d
            if self.encoding == DepthEncoding.Colorizer:
                depth_map = self.input.depth_map
            elif self.encoding == DepthEncoding.Linear:
                depth_map = self.encode_depth_information(self.input, linear_interpolate, self.bit_depth)
            elif self.encoding == DepthEncoding.Quad:
                depth_map = self.encode_depth_information(self.input, ease_out_quad, self.bit_depth)
            else:
                raise Exception("No encoding method is set!")

            # resize to match rgb image if necessary
            if depth_map.shape != frame.shape:
                h, w = frame.shape[:2]
                depth_map = cv2.resize(depth_map, (w, h))

            rgbd = np.hstack((depth_map, frame))
        else:
            # just send rgb image for testing
            rgbd = frame

        # send rgb-d over spout
        bgrd = cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR)
        self.fbs_client.send(bgrd)

        self.fps_tracer.update()

        # imshow does only work in main thread!
        if threading.current_thread() is threading.main_thread():
            cv2.putText(rgbd, "FPS: %.0f" % self.fps_tracer.smooth_fps,
                        (7, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1, cv2.LINE_AA)

            cv2.imshow("RGB-D FrameBuffer Sharing Demo", rgbd)
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

    def encode_depth_information(self, device: vg.BaseDepthInput,
                                 interpolation: Callable,
                                 bit_depth: int) -> np.ndarray:
        # prepare information
        min_value = round(self.min_distance / self.depth_units)
        max_value = round(self.max_distance / self.depth_units)
        d_value = max_value - min_value
        total_unique_values = pow(2, bit_depth) - 1

        # read depth, clip, normalize and map
        depth = device.depth_buffer
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
    def add_params(parser: argparse.ArgumentParser):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RGB-D framebuffer sharing demo for visiongraph")
    vg.add_enum_choice_argument(parser, DepthEncoding, "--depth-encoding",
                                help="Method how the depth map will be encoded")
    parser.add_argument("--min-distance", type=float, default=0, help="Min distance to perceive by the camera.")
    parser.add_argument("--max-distance", type=float, default=6, help="Max distance to perceive by the camera.")
    parser.add_argument("--bit-depth", type=int, default=8, choices=[8, 16],
                        help="Encoding output bit depth (default: 8).")
    parser.add_argument("--stream-name", type=str, default="RGBDStream", help="Spout / Syphon stream name.")

    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)

    input_group.add_argument("--no-filter", action="store_true", help="Disable realsense image filter.")

    args = parser.parse_args()

    if issubclass(args.input, vg.BaseDepthInput):
        args.depth = True

    if issubclass(args.input, vg.RealSenseInput):
        logging.info("setting realsense options")
        args.depth = True
        args.color_scheme = vg.RealSenseColorScheme.WhiteToBlack

        if not args.no_filter:
            args.rs_filter = [rs.spatial_filter, rs.temporal_filter, rs.hole_filling_filter]

    if issubclass(args.input, vg.AzureKinectInput):
        args.k4a_align = True

    # create frame buffer sharing client
    fbs_client = FrameBufferSharingServer.create(args.stream_name)

    # run pipeline
    pipeline = DemoPipeline(args.input(), fbs_client, args.depth_encoding,
                            args.min_distance, args.max_distance, args.bit_depth)
    pipeline.configure(args)
    pipeline.open()
