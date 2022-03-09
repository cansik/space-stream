import numpy as np
from numba import njit, prange

from spacestream.codec import ENABLE_FAST_MATH, ENABLE_PARALLEL
from spacestream.codec.DepthCodec import DepthCodec

INDEPENDENT_VALUES = 1529


class UniformHueColorization(DepthCodec):
    """
    This codec implements the intel white paper Uniform Hue Colorization:
    https://dev.intelrealsense.com/docs/depth-image-compression-by-colorization-for-intel-realsense-depth-cameras
    """

    def encode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        super().prepare_encode_buffer(depth)
        self._pencode(depth, self.encode_buffer, d_min, d_max)
        return self.encode_buffer

    @staticmethod
    @njit(parallel=ENABLE_PARALLEL, fastmath=ENABLE_FAST_MATH)
    def _pencode(depth: np.ndarray, result: np.ndarray, d_min: float, d_max: float):
        h, w = depth.shape[:2]

        for i in prange(w * h):
            x = i % w
            y = i // w

            d = depth[y, x]

            # create rgb
            r, g, b = 0, 0, 0

            # normalize depth
            d_norm = ((d - d_min) / (d_max - d_min)) * INDEPENDENT_VALUES

            # red
            if 0 <= d_norm <= 255 or 1275 < d_norm <= 1529:
                r = 255
            elif 255 < d_norm <= 510:
                r = 255 - d_norm
            elif 510 < d_norm <= 1020:
                r = 0
            elif 1020 < d_norm <= 1275:
                r = d_norm - 1020

            # green
            if 0 < d_norm <= 255:
                g = d_norm
            elif 255 < d_norm <= 510:
                g = 255
            elif 510 < d_norm <= 765:
                g = 765 - d_norm
            elif 765 < d_norm <= 1529:
                g = 0

            # blue
            if 0 < d_norm <= 765:
                b = 0
            elif 765 < d_norm <= 1020:
                b = d_norm - 765
            elif 1020 < d_norm <= 1275:
                b = 255
            elif 1275 < d_norm <= 1529:
                b = 1275 - d_norm

            result[y, x, 0] = b
            result[y, x, 1] = g
            result[y, x, 2] = r

    def decode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        super().prepare_decode_buffer(depth)
        self._pdecode(depth.astype(np.uint16), self.decode_buffer, d_min, d_max)
        return self.decode_buffer

    @staticmethod
    @njit(parallel=ENABLE_PARALLEL, fastmath=ENABLE_FAST_MATH)
    def _pdecode(depth: np.ndarray, result: np.ndarray, d_min: float, d_max: float):
        h, w = depth.shape[:2]

        for i in prange(w * h):
            x = i % w
            y = i // w

            r, g, b = depth[y, x]

            r = int(r)
            g = int(g)
            b = int(b)

            d_norm = 0

            if r >= g and r >= b and g >= b:
                d_norm = g - b
            elif r >= g and r >= b and g < b:
                d_norm = g - b + 1529
            elif g >= r and g >= b:
                d_norm = b - r + 510
            elif b >= g and b >= r:
                d_norm = r - g + 1020

            d_recovery = d_min + (((d_max - d_min) * d_norm) / INDEPENDENT_VALUES)
            result[y, x] = d_recovery
