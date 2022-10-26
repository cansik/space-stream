from dataclasses import dataclass


@dataclass
class Vector2:
    x: float = 0.0
    y: float = 0.0


@dataclass
class StreamSize:
    width: float = 0.0
    height: float = 0.0


@dataclass
class RangeValue:
    min: float = 0.0
    max: float = 0.0


@dataclass
class Intrinsics:
    principle: Vector2 = Vector2()
    focal: Vector2 = Vector2()


@dataclass
class StreamInformation:
    serial: str = ""
    resolution: StreamSize = StreamSize()
    intrinsics: Intrinsics = Intrinsics()
    distance: RangeValue = RangeValue()
