import numpy as np
from numba import njit, prange

from spacestream.codec import ENABLE_FAST_MATH, ENABLE_PARALLEL
from spacestream.codec.DepthCodec import DepthCodec

INDEPENDENT_VALUES = 1529


class LinearCodec(DepthCodec):
    def encode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        super().prepare_encode_buffer(depth)
        self._pencode(depth, self.encode_buffer, d_min, d_max)
        return self.encode_buffer

    @staticmethod
    @njit(parallel=ENABLE_PARALLEL, fastmath=ENABLE_FAST_MATH)
    def _pencode(depth: np.ndarray, result: np.ndarray, d_min: float, d_max: float):
        h, w = depth.shape[:2]

        d_value = d_max - d_min
        total_unique_values = pow(2, 16) - 1

        for i in prange(w * h):
            x = i % w
            y = i // w

            d = depth[y, x]

            # set 0 (no-data points) to max value
            if d == 0:
                d = d_max

            d = min(max(d, d_min), d_max)

            d = (d - d_min) * total_unique_values
            d = total_unique_values - d
            d = int(d / d_value)

            # bgr output encoding
            result[y, x, 2] = d // 256 & 0xFF
            result[y, x, 1] = (d >> 8) & 0xFF
            result[y, x, 0] = d & 0xFF

    def decode(self, depth: np.ndarray, d_min: float, d_max: float, decode_8bit: bool = False) -> np.ndarray:
        self.prepare_decode_buffer(depth)

        # todo: currently does not encode correctly, implemented correct scaling
        # frame comes in as RGB (R=8bit depth, GB=16bit depth)
        if decode_8bit:
            self.decode_buffer[:, :] = depth[:, :, 0] * 255
        else:
            b = depth[:, :, 2]
            g = depth[:, :, 1]
            self.decode_buffer[:, :] = (g << 8 | b)

        return self.decode_buffer
