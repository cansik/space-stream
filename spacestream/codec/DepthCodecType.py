from enum import Enum
from functools import partial

from spacestream.codec.RealSenseColorizer import RealSenseColorizer


def _init_linear_codec():
    from spacestream.codec.LinearCodec import LinearCodec
    return LinearCodec()


def _init_uniform_hue():
    from spacestream.codec.UniformHueColorization import UniformHueColorization
    return UniformHueColorization()


def _init_inverse_hue():
    from spacestream.codec.InverseHueColorization import InverseHueColorization
    return InverseHueColorization()


class DepthCodecType(Enum):
    Linear = partial(_init_linear_codec)
    UniformHue = partial(_init_uniform_hue)
    InverseHue = partial(_init_inverse_hue)
    RSColorizer = RealSenseColorizer
