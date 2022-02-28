import logging
from functools import partial

import configargparse
from visiongraph.input import add_input_step_choices

from spacestream.DepthEncoding import DepthEncoding
from spacestream.SpaceStreamPipeline import SpaceStreamPipeline
from spacestream.fbs.FrameBufferSharingServer import FrameBufferSharingServer
from spacestream.ui.MainWindow import MainWindow

import visiongraph as vg
import pyrealsense2 as rs
import open3d as o3d

segmentation_networks = {
    "mediapipe": partial(vg.MediaPipePoseEstimator.create, vg.PoseModelComplexity.Normal),
    "mediapipe-light": partial(vg.MediaPipePoseEstimator.create, vg.PoseModelComplexity.Light),
    "mediapipe-heavy": partial(vg.MediaPipePoseEstimator.create, vg.PoseModelComplexity.Heavy),

    "maskrcnn": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_608_FP32),
    "maskrcnn-eff-480": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_480_FP16),
    "maskrcnn-eff-608": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_608_FP16),
    "maskrcnn-res50-768": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.ResNet50_1024x768_FP16),
    "maskrcnn-res101-800": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.ResNet101_1344x800_FP16)
}


def parse_args():
    parser = configargparse.ArgumentParser(prog="spacestream",
                                           description="RGB-D framebuffer sharing demo for visiongraph")
    parser.add_argument("-c", "--config", required=False, is_config_file=True, help="Configuration file path.")
    vg.add_logging_parameter(parser)
    vg.add_enum_choice_argument(parser, DepthEncoding, "--depth-encoding",
                                help="Method how the depth map will be encoded")
    parser.add_argument("--min-distance", type=float, default=0, help="Min distance to perceive by the camera.")
    parser.add_argument("--max-distance", type=float, default=6, help="Max distance to perceive by the camera.")
    parser.add_argument("--bit-depth", type=int, default=8, choices=[8, 16],
                        help="Encoding output bit depth (default: 8).")
    parser.add_argument("--stream-name", type=str, default="RGBDStream", help="Spout / Syphon stream name.")

    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)
    input_group.add_argument("--midas", action="store_true", help="Use midas for depth capture.")

    masking_group = parser.add_argument_group("masking")
    masking_group.add_argument("--mask", action="store_true", help="Apply mask by segmentation algorithm.")
    vg.add_step_choice_argument(masking_group, segmentation_networks, name="--segnet", default="mediapipe",
                                help="Segmentation Network", add_params=False)

    debug_group = parser.add_argument_group("debug")
    debug_group.add_argument("--no-filter", action="store_true", help="Disable realsense image filter.")
    debug_group.add_argument("--no-preview", action="store_true", help="Disable preview to speed.")
    debug_group.add_argument("--record", action="store_true", help="Record output into recordings folder.")

    return parser.parse_args()


def main():
    args = parse_args()
    vg.setup_logging(args.loglevel)

    if issubclass(args.input, vg.BaseDepthInput):
        args.depth = True

    if issubclass(args.input, vg.RealSenseInput):
        logging.info("setting realsense options")
        args.depth = True
        args.color_scheme = vg.RealSenseColorScheme.WhiteToBlack

        if not args.no_filter:
            args.rs_filter = [rs.spatial_filter, rs.temporal_filter]

    if issubclass(args.input, vg.AzureKinectInput):
        args.k4a_align = True

    # create frame buffer sharing client
    fbs_client = FrameBufferSharingServer.create(args.stream_name)

    show_ui = not args.no_preview

    # run pipeline
    pipeline = SpaceStreamPipeline(args.stream_name, args.input(), fbs_client, args.depth_encoding,
                                   args.min_distance, args.max_distance, args.bit_depth,
                                   args.record, args.mask, args.segnet(), args.midas,
                                   multi_threaded=show_ui, handle_signals=not show_ui)
    pipeline.configure(args)

    if show_ui:
        app = o3d.visualization.gui.Application.instance
        app.initialize()

        win = MainWindow(pipeline)
        app.run()
    else:
        pipeline.open()


if __name__ == "__main__":
    main()
