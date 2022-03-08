from abc import ABC, abstractmethod

import numpy as np


class DepthCodec(ABC):

    @abstractmethod
    def encode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        pass

    @abstractmethod
    def decode(self, depth: np.ndarray, d_min: float, d_max: float) -> np.ndarray:
        pass