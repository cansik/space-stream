import numpy as np

from spacestream.codec.DepthCodec import DepthCodec
import pyrealsense2 as rs


class RealSenseColorizer(DepthCodec):
    def __init__(self):
        super().__init__()
        print("colorizer instantiated")
        self.colorizer = rs.colorizer()
        self.colorizer.set_option(rs.option.color_scheme, 9.0)
        self.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)

    def encode(self, depth: rs.depth_frame, d_min: float, d_max: float) -> np.ndarray:
        self.colorizer.set_option(rs.option.min_distance, d_min)
        self.colorizer.set_option(rs.option.max_distance, d_max)

        colorized_frame = self.colorizer.colorize(depth)
        result = np.asanyarray(colorized_frame.get_data())
        return result

    def decode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        raise Exception("RealSenseColorizer does not support frame decoding.")
