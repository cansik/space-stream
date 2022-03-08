from enum import Enum

from spacestream.codec.LinearCodec import LinearCodec
from spacestream.codec.UniformHueColorization import UniformHueColorization


class DepthCodecType(Enum):
    Linear = LinearCodec()
    UniformHue = UniformHueColorization()
