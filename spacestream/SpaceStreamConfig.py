import duit.ui as dui
import vector
from duit.arguments.Argument import Argument
from duit.model.DataField import DataField
from duit.settings.Setting import Setting

from duit.ui.ContainerHelper import ContainerHelper

from spacestream.codec.DepthCodecType import DepthCodecType


class SpaceStreamConfig:
    def __init__(self):
        container = ContainerHelper(self)

        with container.section("Pipeline"):
            self.pipeline_fps = DataField("-") | dui.Text("Pipeline FPS", readonly=True)
            self.encoding_time = DataField("-") | dui.Text("Encoding Time", readonly=True)
            self.disable_preview = DataField(False) | dui.Boolean("Disable Preview")
            self.record = DataField(False) | dui.Boolean("Record")

        with container.section("Intrinsics"):
            self.serial_number = DataField("-") | dui.Text("Serial", readonly=True, copy_content=True)
            self.intrinsics_res = DataField("-") | dui.Text("Resolution", readonly=True, copy_content=True)
            self.intrinsics_principle = DataField("-") | dui.Text("Principle Point", readonly=True, copy_content=True)
            self.intrinsics_focal = DataField("-") | dui.Text("Focal Point", readonly=True, copy_content=True)
            self.normalize_intrinsics = DataField(True) | dui.Boolean("Normalize Intrinsics")

        with container.section("Depth"):
            self.codec = DataField(DepthCodecType.UniformHue) | dui.Enum("Codec")
            self.min_distance = DataField(0.0) | dui.Number("Min Distance")
            self.max_distance = DataField(6.0) | dui.Number("Max Distance")

        with container.section("3D View"):
            self.enable_3d_view = DataField(False) | dui.Boolean("Enabled")

        with container.section("Masking"):
            self.masking = DataField(False) | dui.Boolean("Enabled")

        with container.section("FB Sharing"):
            self.stream_name = DataField("space-stream") | dui.Text("Stream Name")
