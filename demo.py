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

    Linear_8bit = 2,
    Quad_8bit = 3,
    Cubic_8bit = 4,
    Quart_8bit = 5,
    Quint_8bit = 6,


def linear_interpolate(x):
    return x


def ease_out_quad(x):
    # ease_in_quad: x => x * x
    return x * (2 - x)


def ease_out_cubic(x):
    # ease_in_cubic: x => x * x * x
    x = x - 1
    return np.power(x, 3) + 1


def ease_out_quart(x):
    # ease_in_cubic: x => x * x * x * x
    x = x - 1
    return 1 - np.power(x, 4)


def ease_out_quint(x):
    # ease_in_cubic: x => x * x * x * x
    x = x - 1
    return 1 + np.power(x, 5)


class DemoPipeline(vg.BaseGraph):

    def __init__(self, input: vg.BaseInput, fbs_client: FrameBufferSharingServer,
                 encoding: DepthEncoding = DepthEncoding.Colorizer, min_distance: float = 0, max_distance: float = 6):
        super().__init__(False, False, handle_signals=True)

        self.input = input
        self.fbs_client = fbs_client

        self.encoding = encoding
        self.min_distance = min_distance
        self.max_distance = max_distance

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

        if isinstance(self.input, vg.RealSenseInput):
            # read depth map and create rgb-d

            if self.encoding == DepthEncoding.Colorizer:
                depth_map = self.input.depth_map
            elif self.encoding == DepthEncoding.Linear_8bit:
                depth_map = self.encode_depth_information(self.input, linear_interpolate)
            elif self.encoding == DepthEncoding.Quad_8bit:
                depth_map = self.encode_depth_information(self.input, ease_out_quad)
            elif self.encoding == DepthEncoding.Cubic_8bit:
                depth_map = self.encode_depth_information(self.input, ease_out_cubic)
            elif self.encoding == DepthEncoding.Quart_8bit:
                depth_map = self.encode_depth_information(self.input, ease_out_quart)
            elif self.encoding == DepthEncoding.Quint_8bit:
                depth_map = self.encode_depth_information(self.input, ease_out_quint)
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

        # imshow does only work in main thread!
        if threading.current_thread() is threading.main_thread():
            cv2.imshow("RGB-D FrameBuffer Sharing Demo", rgbd)
            key_code = cv2.waitKey(15) & 0xFF
            if key_code == 27:
                self.close()

            key = chr(key_code).lower()
            if key == "h":
                print("Use numbers to toggle through encodings (example: Colorizer = 0, Linear = 1, ...)")

            if key.isnumeric():
                index = int(key)
                encodings = list({item.name: item for item in list(DepthEncoding)}.values())

                if index < len(encodings):
                    self.encoding = encodings[index]
                    print(f"Switch to {self.encoding} ({index})")

    def encode_depth_information(self, device: vg.RealSenseInput,
                                 interpolation: Callable,
                                 bit_depth: int = 8) -> np.ndarray:
        # prepare information
        depth_unit = device.depth_frame.get_units()
        min_value = round(self.min_distance / depth_unit)
        max_value = round(self.max_distance / depth_unit)
        d_value = max_value - min_value
        total_unique_values = pow(2, bit_depth) - 1

        # read depth, clip, normalize and map
        depth = np.asarray(device.depth_frame.data, dtype=np.float)
        depth[depth == 0] = max_value  # set 0 (no-data points) to max value
        depth = np.clip(depth, min_value, max_value)
        depth = (depth - min_value) / d_value  # normalize

        depth = interpolation(depth)
        depth = 1.0 - depth  # flip

        # convert to new bit range
        depth = (depth * total_unique_values).astype(np.uint8)

        # map to RGB image
        return cv2.cvtColor(depth, cv2.COLOR_GRAY2RGB)

    @staticmethod
    def add_params(parser: argparse.ArgumentParser):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RGB-D framebuffer sharing demo for visiongraph")
    vg.add_enum_choice_argument(parser, DepthEncoding, "--depth-encoding",
                                help="Method how the depth map will be encoded")
    parser.add_argument("--min-distance", type=float, default=0, help="Min distance to perceive by the camera.")
    parser.add_argument("--max-distance", type=float, default=10, help="Max distance to perceive by the camera.")

    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)

    input_group.add_argument("--no-filter", action="store_true", help="Disable realsense image filter.")

    args = parser.parse_args()

    if issubclass(args.input, vg.RealSenseInput):
        logging.info("setting realsense options")
        args.depth = True
        args.color_scheme = vg.RealSenseColorScheme.WhiteToBlack

        if not args.no_filter:
            args.rs_filter = [rs.spatial_filter, rs.temporal_filter, rs.hole_filling_filter]

    # create frame buffer sharing client
    fbs_client = FrameBufferSharingServer.create("RGBDStream")

    # run pipeline
    pipeline = DemoPipeline(args.input(), fbs_client, args.depth_encoding)
    pipeline.configure(args)
    pipeline.open()
