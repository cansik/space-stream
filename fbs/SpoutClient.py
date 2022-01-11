import logging
from argparse import ArgumentParser, Namespace
from typing import Optional

import SpoutGL
import numpy as np
from OpenGL import GL

from fbs.FrameBufferSharingClient import FrameBufferSharingClient


class SpoutClient(FrameBufferSharingClient):
    def __init__(self, name: str = "SpoutClient"):
        super().__init__(name)
        self.ctx: Optional[SpoutGL.SpoutSender] = None

    def setup(self):
        # setup spout
        self.ctx = SpoutGL.SpoutSender()
        self.ctx.setSenderName(self.name)

    def send(self, frame: np.array):
        h, w = frame.shape[:2]
        success = self.ctx.sendImage(frame, w, h, GL.GL_RGB, False, 0)

        if not success:
            logging.warning("Could not send spout image.")
            return

        # Indicate that a frame is ready to read
        self.ctx.setFrameSync(self.name)

    def release(self):
        self.ctx.releaseSender()

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass