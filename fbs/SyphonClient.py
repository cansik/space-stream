from argparse import Namespace, ArgumentParser
from typing import Optional


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

from fbs.FrameBufferSharingClient import FrameBufferSharingClient


class SyphonClient(FrameBufferSharingClient):
    def __init__(self, name: str = "SyphonClient"):
        super().__init__(name)
        self.ctx: Optional[syphonpy.SyphonServer] = None
        self.texture: Optional[glGenTextures] = None

    def setup(self):
        # setup spout
        self.ctx = syphonpy.SyphonServer(self.name)
        self.texture = glGenTextures(1)

    def send(self, frame: np.array):
        h, w = frame.shape[:2]

        self._numpy_to_texture(frame, w, h)
        self.ctx.publish_frame_texture(self.texture, syphonpy.MakeRect(0, 0, w, h), syphonpy.MakeSize(w, h), False)

    def release(self):
        self.ctx.stop()

    def _numpy_to_texture(self, image: np.ndarray, w: int, h: int):
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

        gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGB, w, h, GL_RGB, GL_UNSIGNED_BYTE, image)

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass
