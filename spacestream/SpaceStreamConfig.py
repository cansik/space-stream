import duit.ui as dui
from duit.arguments.Argument import Argument
from duit.model.DataField import DataField
from duit.settings.Setting import Setting
from duit.ui.ContainerHelper import ContainerHelper
from duit_osc.OscEndpoint import OscEndpoint

from spacestream.codec.DepthCodecType import DepthCodecType


class SpaceStreamConfig:
    def __init__(self):
        self.is_loading = False
        container = ContainerHelper(self)

        with container.section("Pipeline"):
            self.pipeline_fps = DataField("-") | dui.Text("Pipeline FPS", readonly=True) | Setting(exposed=False)
            self.encoding_time = DataField("-") | dui.Text("Encoding Time", readonly=True) | Setting(exposed=False)
            self.disable_preview = DataField(False) | dui.Boolean("Disable Preview")
            self.record = DataField(False) | dui.Boolean("Record") | Argument(help="Record output into recordings folder.") | OscEndpoint()

        with container.section("View Parameter"):
            self.display_vertical_stack = DataField(True) | dui.Boolean("Display Vertical Stack") | Argument(help="Preview images vertically.")
            self.display_depth_map = DataField(False) | dui.Boolean("Display Depth Map")

        with container.section("Intrinsics"):
            self.serial_number = DataField("-") | dui.Text("Serial", readonly=True, copy_content=True) | Setting(exposed=False)
            self.intrinsics_res = DataField("-") | dui.Text("Resolution", readonly=True, copy_content=True) | Setting(exposed=False)
            self.intrinsics_principle = DataField("-") | dui.Text("Principle Point", readonly=True, copy_content=True) | Setting(exposed=False)
            self.intrinsics_focal = DataField("-") | dui.Text("Focal Point", readonly=True, copy_content=True) | Setting(exposed=False)
            self.normalize_intrinsics = DataField(True) | dui.Boolean("Normalize Intrinsics")

        with container.section("Depth"):
            self.codec = DataField(DepthCodecType.UniformHue) | dui.Enum("Codec") | Argument(help="Codec how the depth map will be encoded.") | OscEndpoint()
            self.min_distance = DataField(0.0) | dui.Number("Min Distance") | Argument(help="Min distance to perceive by the camera.") | OscEndpoint()
            self.max_distance = DataField(6.0) | dui.Number("Max Distance") | Argument(help="Max distance to perceive by the camera.") | OscEndpoint()
            self.depth_rectification = DataField(False) | dui.Boolean("Depth Rectification", tooltip="Undistort depth image") | Argument(help="Undistort depth image") | OscEndpoint()

        with container.section("Camera"):
            self.cam_auto_exposure = DataField(True) | dui.Boolean("Auto Exposure") | OscEndpoint()
            self.cam_exposure = DataField(33) | dui.Slider("Exposure", 1, 33) | OscEndpoint()
            self.cam_iso = DataField(128) | dui.Slider("ISO", 0, 255) | OscEndpoint()
            self.cam_auto_white_balance = DataField(True) | dui.Boolean("Auto White Balance") | OscEndpoint()
            self.cam_white_balance = DataField(6000) | dui.Slider("White Balance", 2500, 12500) | OscEndpoint()

        with container.section("Masking"):
            self.masking = DataField(False) | dui.Boolean("Enabled") | OscEndpoint()

        with container.section("Frame Buffer Sharing"):
            self.stream_name = DataField("stream") | dui.Text("Stream Name") | Argument(help="Spout / Syphon / NDI stream name.") | OscEndpoint()
