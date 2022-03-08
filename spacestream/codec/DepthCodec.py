import logging
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class DepthCodec(ABC):
    def __init__(self):
        self.encode_buffer: Optional[np.ndarray] = None
        self.decode_buffer: Optional[np.ndarray] = None

    def prepare_encode_buffer(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        if not isinstance(self.encode_buffer, np.ndarray) \
                or h != self.encode_buffer.shape[0] or w != self.encode_buffer.shape[1]:
            self.encode_buffer = np.zeros(shape=(h, w, 3), dtype=np.uint8)

    def prepare_decode_buffer(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        if not isinstance(self.decode_buffer, np.ndarray) \
                or h != self.decode_buffer.shape[0] or w != self.decode_buffer.shape[1]:
            self.decode_buffer = np.zeros(shape=(h, w, 3), dtype=np.uint8)

    @abstractmethod
    def encode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        pass

    @abstractmethod
    def decode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        pass
