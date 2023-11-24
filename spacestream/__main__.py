# fix conda load dll problem
import faulthandler
import os
from pathlib import Path

from duit.arguments.Arguments import DefaultArguments
from visiongui.ui.UIContext import UIContext

from spacestream.SpaceStreamApp import SpaceStreamApp
from spacestream.SpaceStreamConfig import SpaceStreamConfig
from spacestream.ui.MainWindow import MainWindow

os.environ["CONDA_DLL_SEARCH_MODIFICATION_ENABLE"] = "1"

import logging
from functools import partial

import configargparse
import numba
from visiongraph.input import add_input_step_choices

from spacestream import codec

import visiongraph as vg
import pyrealsense2 as rs

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


def parse_args(config: SpaceStreamConfig):
    parser = configargparse.ArgumentParser(prog="space-stream",
                                           description="RGB-D framebuffer sharing demo for visiongraph.")
    parser.add_argument("-c", "--config", required=False, is_config_file=True, help="Configuration file path.")
    parser.add_argument("-s", "--settings", type=str, required=False, help="Settings file path (json).")
    vg.add_logging_parameter(parser)

    DefaultArguments.add_arguments(parser, config)

    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)
    input_group.add_argument("--midas", action="store_true", help="Use midas for depth capture.")

    masking_group = parser.add_argument_group("masking")
    vg.add_step_choice_argument(masking_group, segmentation_networks, name="--segnet", default="mediapipe",
                                help="Segmentation Network", add_params=False)

    performance_group = parser.add_argument_group("performance")
    performance_group.add_argument("--parallel", action="store_true", help="Enable parallel for codec operations.")
    performance_group.add_argument("--num-threads", type=int, default=4, help="Number of threads for parallelization.")
    performance_group.add_argument("--no-fastmath", action="store_true", help="Disable fastmath for codec operations.")

    debug_group = parser.add_argument_group("debug")
    debug_group.add_argument("--no-filter", action="store_true", help="Disable realsense image filter.")
    debug_group.add_argument("--no-preview", action="store_true", help="Disable preview to speed.")
    debug_group.add_argument("--record-crf", type=int, default=23, help="Recording compression rate.")
    debug_group.add_argument("--view-pcd", action="store_true", help="Display PCB preview (deprecated, use --view-3d).")
    debug_group.add_argument("--view-3d", action="store_true", help="Display PCB preview.")

    args = parser.parse_args()

    if args.view_pcd:
        args.view_3d = True
    return args


def main():
    config = SpaceStreamConfig()

    args = parse_args(config)
    DefaultArguments.configure(args, config)

    vg.setup_logging(args.loglevel)
    logging.info(f"Logging has ben set to {args.loglevel}")

    if args.loglevel.lower() == "debug" or True:
        faulthandler.enable()

    if args.parallel:
        num_threads = min(numba.config.NUMBA_NUM_THREADS, args.num_threads)
        numba.set_num_threads(num_threads)
        codec.ENABLE_PARALLEL = True
        logging.warning(f"Enable parallel with {num_threads} threads")

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
        args.k4a_align_to_color = True

    show_ui = not args.no_preview

    # create app and graph
    app = SpaceStreamApp(config, args.input(), args.segnet(), multi_threaded=show_ui)
    app.graph.configure(args)

    if args.settings is not None:
        settings_path = Path(args.settings)
        if settings_path.exists():
            app.load_config(settings_path)

    if show_ui:
        with UIContext():
            window = MainWindow(app)

            if args.settings is not None:
                window.menu.settings_file = Path(args.settings)
    else:
        app.graph.open()


if __name__ == "__main__":
    main()
