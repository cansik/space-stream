import numpy as np
from numba import njit, prange

from spacestream.codec.DepthCodec import DepthCodec

INDEPENDENT_VALUES = 1529


class UniformHueColorization(DepthCodec):
    def encode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        result = self._pencode(depth, d_min, d_max)
        return result

    @staticmethod
    @njit
    def _pencode(depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        h, w = depth.shape[:2]
        result = np.zeros(shape=(h, w, 3), dtype=np.uint8)

        for y in range(h):
            for x in range(w):
                d = depth[y, x]

                # create rgb
                r, g, b = 0, 0, 0

                # normalize depth
                d_norm = ((d - d_min) / (d_max - d_min)) * INDEPENDENT_VALUES

                # red
                if 0 <= d_norm <= 255 or 1275 < d_norm <= 1529:
                    r = 255
                elif 255 < d_norm <= 510:
                    r = 255 - d
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
                elif 1024 < d_norm <= 1275:
                    b = 255
                elif 1275 < d_norm <= 1529:
                    b = 1275 - d_norm

                result[y, x, 0] = b
                result[y, x, 1] = g
                result[y, x, 2] = r

        return result

    def decode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        return depth