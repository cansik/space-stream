from enum import Enum


class DepthEncoding(Enum):
    Colorizer = 1,
    Linear = 2,
    LinearRaw = 4,
    UniformHue = 5,
    Quad = 3,
