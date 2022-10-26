import cv2
import numpy as np

from spacestream.codec.DepthCodec import DepthCodec
import pyrealsense2 as rs


class RealSenseColorizer(DepthCodec):
    def __init__(self):
        super().__init__()
        self.colorizer = rs.colorizer()
        self.colorizer.set_option(rs.option.color_scheme, 9.0)
        self.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)

    def encode(self, depth: rs.depth_frame, d_min: float, d_max: float) -> np.ndarray:
        self.colorizer.set_option(rs.option.min_distance, d_min / 1000)
        self.colorizer.set_option(rs.option.max_distance, d_max / 1000)

        colorized_frame = self.colorizer.colorize(depth)
        result = np.asanyarray(colorized_frame.get_data())
        result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)

        # replace red color
        result[np.all(result == (0, 0, 255), axis=-1)] = (0, 0, 0)
        return result

    def decode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        raise Exception("RealSenseColorizer does not support frame decoding.")
