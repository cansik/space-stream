from abc import ABC, abstractmethod
from sys import platform
from typing import Optional, Any, Sequence

import numpy as np
import visiongraph as vg


class FrameBufferSharingClient(vg.BaseInput, ABC):
    def __init__(self, server_name: str):
        self.server_name = server_name

    @abstractmethod
    def receive_frame(self) -> np.array:
        pass

    @abstractmethod
    def receive_texture(self, texture_handle: int):
        pass

    def process(self, data: None) -> np.ndarray:
        return self.receive_frame()

    def read(self) -> (int, Optional[np.ndarray]):
        ts = vg.current_millis()
        return ts, self.receive_frame()

    @abstractmethod
    def get_available_servers(self) -> Sequence[str]:
        pass

    @abstractmethod
    def select_server(self, server_name: str):
        pass

    @staticmethod
    def create(server_name: str = "", create_gl_context: bool = True):
        if platform.startswith("darwin"):
            from spacestream.fbs.syphon.SyphonClient import SyphonClient
            return SyphonClient(server_name, create_gl_context)
        elif platform.startswith("win"):
            from spacestream.fbs.spout.SpoutClient import SpoutClient
            return SpoutClient(server_name)
        else:
            raise Exception(f"Platform {platform} is not supported!")
