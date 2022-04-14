import logging
from argparse import ArgumentParser, Namespace
from typing import Sequence, Optional, Tuple

import numpy as np
import SpoutGL
from OpenGL import GL
from itertools import repeat
import array

from spacestream.fbs.FrameBufferSharingClient import FrameBufferSharingClient


class SpoutClient(FrameBufferSharingClient):
    def __init__(self, server_name: str):
        super().__init__(server_name)

        self.ctx: Optional[SpoutGL.SpoutReceiver] = None

    def setup(self):
        self.ctx = SpoutGL.SpoutReceiver()

        # setup syphon
        if self.server_name != "":
            self.select_server(self.server_name)

    def receive_frame(self) -> np.array:
        pass

    def receive_texture(self, texture_handle: int):
        pass

    def release(self):
        self.ctx.releaseReceiver()

    def get_available_servers(self) -> Sequence[str]:
        sender_names = SpoutGL.spoutSenderNames()
        sender_count = sender_names.getSenderCount()
        names = sender_names.getSenderNames()
        infos = sender_names.getSenderNameInfo(0)
        return sender_count

    def select_server(self, server_name: str):
        self.ctx.setReceiverName(server_name)
        self.server_name = server_name

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass
