from argparse import Namespace, ArgumentParser
from typing import Optional, Any

import cv2
import glfw


def monkeypatch_ctypes():
    import os
    import ctypes.util
    uname = os.uname()
    if uname.sysname == "Darwin" and uname.release >= "20.":
        real_find_library = ctypes.util.find_library

        def find_library(name):
            if name in {"OpenGL", "GLUT"}:  # add more names here if necessary
                return f"/System/Library/Frameworks/{name}.framework/{name}"
            return real_find_library(name)

        ctypes.util.find_library = find_library
    return


# fixes opengl import on MacOS
monkeypatch_ctypes()

import numpy as np
import syphonpy

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

from spacestream.fbs.FrameBufferSharingServer import FrameBufferSharingServer


class SyphonServer(FrameBufferSharingServer):
    def __init__(self, name: str = "SyphonServer"):
        super().__init__(name)

        self.ctx: Optional[syphonpy.SyphonServer] = None
        self.texture: Optional[glGenTextures] = None

        self._window: Optional[Any] = None

    def setup(self):
        # setup spout
        self._create_gl_context()

        self.ctx = syphonpy.SyphonServer(self.name)
        if self.ctx.error_state():
            logging.error("error in syphonserver")
        self.texture = glGenTextures(1)

    def send(self, frame: np.array):
        h, w = frame.shape[:2]

        self._numpy_to_texture(frame, w, h)
        self.ctx.publish_frame_texture(self.texture, syphonpy.MakeRect(0, 0, w, h), syphonpy.MakeSize(w, h), False)

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
