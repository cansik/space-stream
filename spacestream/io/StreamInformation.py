from dataclasses import dataclass, field


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
    principle: Vector2 = field(default_factory=Vector2)
    focal: Vector2 = field(default_factory=Vector2)


@dataclass
class StreamInformation:
    serial: str = ""
    resolution: StreamSize = field(default_factory=StreamSize)
    intrinsics: Intrinsics = field(default_factory=Intrinsics)
    distance: RangeValue = field(default_factory=RangeValue)
