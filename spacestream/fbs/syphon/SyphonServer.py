from argparse import Namespace, ArgumentParser
from typing import Optional, Any

import cv2
import glfw

import numpy as np
import syphonpy

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from spacestream.fbs.FrameBufferSharingServer import FrameBufferSharingServer
from spacestream.fbs.syphon import SyphonUtils


class SyphonServer(FrameBufferSharingServer):
    def __init__(self, name: str = "SyphonServer", create_gl_context: bool = True):
        super().__init__(name)

        self.ctx: Optional[syphonpy.SyphonServer] = None
        self.texture_handle: Optional[glGenTextures] = None

        self.create_gl_context = create_gl_context
        self._window_handle: Optional[int] = None

    def setup(self):
        # setup GL context
        if self.create_gl_context:
            self._window_handle = SyphonUtils.create_gl_context()

        print(f"Window Handle: {self._window_handle}")

        # setup spout
        self.ctx = syphonpy.SyphonServer(self.name)
        if self.ctx.error_state():
            logging.error("error in syphonserver")
        self.texture_handle = glGenTextures(1)

    def send_frame(self, frame: np.array):
        h, w = frame.shape[:2]

        SyphonUtils.numpy_to_texture(frame, w, h, self.texture_handle)
        self.send_texture(self.texture_handle, w, h, False)

    def send_texture(self, texture_id: int, width: int, height: int, is_flipped: bool = False):
        self.ctx.publish_frame_texture(texture_id,
                                       syphonpy.MakeRect(0, 0, width, height),
                                       syphonpy.MakeSize(width, height), is_flipped)

    def send_fbo(self, fbo_id: int, width: int, height: int, is_flipped: bool = False):
        # todo: test if this works
        # maybe test out https://gist.github.com/ZeroStride/3156985

        glBindFramebuffer(GL_FRAMEBUFFER, fbo_id)
        self.send_texture(0, width, height, is_flipped)
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def release(self):
        self.ctx.stop()
        SyphonUtils.release_gl_context(self._window_handle)

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass
