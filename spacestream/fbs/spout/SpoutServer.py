import logging
from argparse import ArgumentParser, Namespace
from typing import Optional

import SpoutGL
import cv2
import numpy as np
from OpenGL import GL

from spacestream.fbs.FrameBufferSharingServer import FrameBufferSharingServer


class SpoutServer(FrameBufferSharingServer):
    def __init__(self, name: str = "SpoutServer"):
        super().__init__(name)
        self.ctx: Optional[SpoutGL.SpoutSender] = None

    def setup(self):
        # setup spout
        self.ctx = SpoutGL.SpoutSender()
        self.ctx.setSenderName(self.name)

    def send_frame(self, frame: np.array, send_alpha: bool = True):
        h, w = frame.shape[:2]

        if send_alpha and frame.shape[2] < 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)

        success = self.ctx.sendImage(frame, w, h, GL.GL_RGBA, False, 0)

        if not success:
            logging.warning("Could not send spout image.")
            return

        # Indicate that a frame is ready to read
        self.ctx.setFrameSync(self.name)

    def send_texture(self, texture, width: int, height: int, is_flipped: bool = False):
        # todo: implemented texture sending
        pass

    def release(self):
        self.ctx.releaseSender()

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass