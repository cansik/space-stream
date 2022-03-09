from spacestream.codec.UniformHueColorization import UniformHueColorization


class InverseHueColorization(UniformHueColorization):
    def __init__(self):
        super().__init__(inverse_transform=True)
