from abc import ABC, abstractmethod
from sys import platform
import numpy as np
from visiongraph.PipelineNode import PipelineNode


class FrameBufferSharingClient(PipelineNode, ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def send(self, frame: np.array):
        pass

    @staticmethod
    def create(name: str):
        if platform.startswith("darwin"):
            from fbs.SyphonClient import SyphonClient
            return SyphonClient(name)
        elif platform.startswith("win"):
            from fbs.SpoutClient import SpoutClient
            return SpoutClient(name)
        else:
            raise Exception(f"Platform {platform} is not supported!")
