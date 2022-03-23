from typing import Optional

import cv2
import glfw
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *


def numpy_to_texture(image: np.ndarray, w: int, h: int, texture: int):
    # flip image
    image = cv2.flip(image, 0)

    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

    gluBuild2DMipmaps(GL_TEXTURE_2D, GL_RGB, w, h, GL_RGB, GL_UNSIGNED_BYTE, image)


def create_gl_context() -> Optional[int]:
    # Initialize the library
    if not glfw.init():
        logging.error("GLFW: could not init glfw")
        return None
    # Set window hint NOT visible
    glfw.window_hint(glfw.VISIBLE, False)

    # Create a windowed mode window and its OpenGL context
    window_handle = glfw.create_window(100, 100, "hidden window", None, None)
    if not window_handle:
        logging.error("GLFW: window error")
        glfw.terminate()
        return None

    glfw.make_context_current(window_handle)
    return window_handle


def release_gl_context(window_handle: Optional[int]):
    if window_handle is not None:
        glfw.destroy_window(window_handle)
        glfw.terminate()
