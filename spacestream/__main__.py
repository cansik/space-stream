import logging
from functools import partial

import configargparse
from visiongraph.input import add_input_step_choices

from spacestream import codec
from spacestream.codec.DepthCodecType import DepthCodecType
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

    # "maskrcnn": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_608_FP32),
    # "maskrcnn-eff-480": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_480_FP16),
    # "maskrcnn-eff-608": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.EfficientNet_608_FP16),
    # "maskrcnn-res50-768": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.ResNet50_1024x768_FP16),
    # "maskrcnn-res101-800": partial(vg.MaskRCNNEstimator.create, vg.MaskRCNNConfig.ResNet101_1344x800_FP16)
}


def parse_args():
    parser = configargparse.ArgumentParser(prog="spacestream",
                                           description="RGB-D framebuffer sharing demo for visiongraph.")
    parser.add_argument("-c", "--config", required=False, is_config_file=True, help="Configuration file path.")
    vg.add_logging_parameter(parser)

    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)
    input_group.add_argument("--midas", action="store_true", help="Use midas for depth capture.")

    masking_group = parser.add_argument_group("masking")
    masking_group.add_argument("--mask", action="store_true", help="Apply mask by segmentation algorithm.")
    vg.add_step_choice_argument(masking_group, segmentation_networks, name="--segnet", default="mediapipe",
                                help="Segmentation Network", add_params=False)

    depth_group = parser.add_argument_group("depth codec")
    vg.add_enum_choice_argument(depth_group, DepthCodecType, "--codec", help="Codec how the depth map will be encoded.")
    depth_group.add_argument("--min-distance", type=float, default=0, help="Min distance to perceive by the camera.")
    depth_group.add_argument("--max-distance", type=float, default=6, help="Max distance to perceive by the camera.")

    performance_group = parser.add_argument_group("performance")
    performance_group.add_argument("--use-parallel", action="store_true", help="Enable parallel for codec operations.")
    performance_group.add_argument("--no-fastmath", action="store_true", help="Disable fastmath for codec operations.")

    output_group = parser.add_argument_group("output")
    output_group.add_argument("--stream-name", type=str, default="RGBDStream", help="Spout / Syphon stream name.")

    debug_group = parser.add_argument_group("debug")
    debug_group.add_argument("--no-filter", action="store_true", help="Disable realsense image filter.")
    debug_group.add_argument("--no-preview", action="store_true", help="Disable preview to speed.")
    debug_group.add_argument("--record", action="store_true", help="Record output into recordings folder.")
    debug_group.add_argument("--record-crf", type=int, default=23, help="Recording compression rate.")
    debug_group.add_argument("--view-pcd", action="store_true", help="Display PCB preview (deprecated, use --view-3d).")
    debug_group.add_argument("--view-3d", action="store_true", help="Display PCB preview.")

    args = parser.parse_args()

    if args.view_pcd:
        args.view_3d = True
    return args


def main():
    args = parse_args()
    vg.setup_logging(args.loglevel)

    if args.use_parallel:
        codec.ENABLE_PARALLEL = True

    if args.no_fastmath:
        codec.ENABLE_FAST_MATH = False

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
    pipeline = SpaceStreamPipeline(args.stream_name, args.input(), fbs_client, args.codec,
                                   args.min_distance, args.max_distance,
                                   args.record, args.mask, args.segnet(), args.midas,
                                   multi_threaded=show_ui, handle_signals=not show_ui)
    pipeline.configure(args)

    if show_ui:
        app = o3d.visualization.gui.Application.instance
        app.initialize()

        win = MainWindow(pipeline, args)
        app.run()
    else:
        pipeline.open()


if __name__ == "__main__":
    main()
