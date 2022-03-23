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


class SyphonServer(FrameBufferSharingServer):
    def __init__(self, name: str = "SyphonServer", gl_context: Optional[Any] = None):
        super().__init__(name, gl_context)

        self.ctx: Optional[syphonpy.SyphonServer] = None
        self.texture: Optional[glGenTextures] = None

        self._window: Optional[Any] = None

    def setup(self):
        # setup GL context
        if self.gl_context is None:
            self._create_gl_context()
        else:
            glfw.make_context_current(self.gl_context)

        # setup spout
        self.ctx = syphonpy.SyphonServer(self.name)
        if self.ctx.error_state():
            logging.error("error in syphonserver")
        self.texture = glGenTextures(1)

    def send_frame(self, frame: np.array):
        h, w = frame.shape[:2]

        self._numpy_to_texture(frame, w, h)
        self.send_texture(self.texture, w, h, False)

    def send_texture(self, texture: glGenTextures, width: int, height: int, is_flipped: bool = False):
        self.ctx.publish_frame_texture(texture,
                                       syphonpy.MakeRect(0, 0, width, height),
                                       syphonpy.MakeSize(width, height), is_flipped)

    def send_fbo(self, fbo_id: int, width: int, height: int):
        # todo: implement this example https://gist.github.com/ZeroStride/3156985
        raise Exception("FBO sharing is not implemented in syphon.")

    def release(self):
        self.ctx.stop()
        self._release_gl_context()

    def _numpy_to_texture(self, image: np.ndarray, w: int, h: int):
        # flip image
        image = cv2.flip(image, 0)

        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

        gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGB, w, h, GL_RGB, GL_UNSIGNED_BYTE, image)

    def _create_gl_context(self):
        # Initialize the library
        if not glfw.init():
            logging.error("GLFW: could not init glfw")
            return
        # Set window hint NOT visible
        glfw.window_hint(glfw.VISIBLE, False)

        # Create a windowed mode window and its OpenGL context
        self._window = glfw.create_window(100, 100, "hidden window", None, None)
        if not self._window:
            logging.error("GLFW: window error")
            glfw.terminate()
            return

        glfw.make_context_current(self._window)

    def _release_gl_context(self):
        if self._window is not None:
            glfw.destroy_window(self._window)
            glfw.terminate()

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass
