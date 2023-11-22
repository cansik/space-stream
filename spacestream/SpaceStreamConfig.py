import duit.ui as dui
from duit.arguments.Argument import Argument
from duit.model.DataField import DataField
from duit.settings.Setting import Setting
from duit.ui.ContainerHelper import ContainerHelper

from spacestream.codec.DepthCodecType import DepthCodecType


class SpaceStreamConfig:
    def __init__(self):
        container = ContainerHelper(self)

        with container.section("Pipeline"):
            self.pipeline_fps = DataField("-") | dui.Text("Pipeline FPS", readonly=True) | Setting(exposed=False)
            self.encoding_time = DataField("-") | dui.Text("Encoding Time", readonly=True) | Setting(exposed=False)
            self.disable_preview = DataField(False) | dui.Boolean("Disable Preview")
            self.record = DataField(False) | dui.Boolean("Record") | Argument(help="Record output into recordings folder.")

        with container.section("Intrinsics"):
            self.serial_number = DataField("-") | dui.Text("Serial", readonly=True, copy_content=True) | Setting(exposed=False)
            self.intrinsics_res = DataField("-") | dui.Text("Resolution", readonly=True, copy_content=True) | Setting(exposed=False)
            self.intrinsics_principle = DataField("-") | dui.Text("Principle Point", readonly=True, copy_content=True) | Setting(exposed=False)
            self.intrinsics_focal = DataField("-") | dui.Text("Focal Point", readonly=True, copy_content=True) | Setting(exposed=False)
            self.normalize_intrinsics = DataField(True) | dui.Boolean("Normalize Intrinsics")

        with container.section("Depth"):
            self.codec = DataField(DepthCodecType.UniformHue) | dui.Enum("Codec") | Argument(help="Codec how the depth map will be encoded.")
            self.min_distance = DataField(0.0) | dui.Number("Min Distance") | Argument(help="Min distance to perceive by the camera.")
            self.max_distance = DataField(6.0) | dui.Number("Max Distance") | Argument(help="Max distance to perceive by the camera.")

        with container.section("Camera"):
            self.cam_auto_exposure = DataField(True) | dui.Boolean("Auto Exposure")
            self.cam_exposure = DataField(33) | dui.Slider("Exposure", 1, 33)
            self.cam_iso = DataField(128) | dui.Slider("ISO", 0, 255)
            self.cam_auto_white_balance = DataField(True) | dui.Boolean("Auto White Balance")
            self.cam_white_balance = DataField(6000) | dui.Slider("White Balance", 2500, 12500)

        # with container.section("3D View"):
        self.enable_3d_view = DataField(False) # | dui.Boolean("Enabled")

        # with container.section("Masking"):
        self.masking = DataField(False) # | dui.Boolean("Enabled")

        with container.section("FB Sharing"):
            self.stream_name = DataField("stream") | dui.Text("Stream Name") | Argument(help="Spout / Syphon stream name.")
