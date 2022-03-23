from abc import ABC, abstractmethod
from sys import platform

import numpy as np
import visiongraph as vg


class FrameBufferSharingServer(vg.GraphNode, ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def send_frame(self, frame: np.array):
        pass

    @abstractmethod
    def send_texture(self, texture, width: int, height: int, is_flipped: bool = False):
        pass

    def process(self, data: np.ndarray) -> None:
        self.send_frame(data)

    @staticmethod
    def create(name: str):
        if platform.startswith("darwin"):
            from spacestream.fbs.syphon.SyphonServer import SyphonServer
            return SyphonServer(name)
        elif platform.startswith("win"):
            from spacestream.fbs.spout.SpoutServer import SpoutServer
            return SpoutServer(name)
        else:
            raise Exception(f"Platform {platform} is not supported!")
