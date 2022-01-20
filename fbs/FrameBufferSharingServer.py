from abc import ABC, abstractmethod
from sys import platform

import numpy as np
import visiongraph as vg


class FrameBufferSharingServer(vg.GraphNode, ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def send(self, frame: np.array):
        pass

    def process(self, data: np.ndarray) -> None:
        self.send(data)

    @staticmethod
    def create(name: str):
        if platform.startswith("darwin"):
            from fbs.SyphonServer import SyphonServer
            return SyphonServer(name)
        elif platform.startswith("win"):
            from fbs.SpoutServer import SpoutServer
            return SpoutServer(name)
        else:
            raise Exception(f"Platform {platform} is not supported!")
