import argparse
import threading

import cv2
import numpy as np
import pyrealsense2 as rs
from visiongraph.Pipeline import Pipeline
from visiongraph.input import RealSenseInput, add_input_step_choices
from visiongraph.input.BaseDepthInput import BaseDepthInput
from visiongraph.model.types.RealSenseColorScheme import RealSenseColorScheme

from fbs.FrameBufferSharingClient import FrameBufferSharingClient


class DemoPipeline(Pipeline):

    def __init__(self, input: RealSenseInput, fbs_client: FrameBufferSharingClient,
                 multi_threaded: bool = False, deamon: bool = False):
        super().__init__(multi_threaded, deamon)

        self.input = input
        self.fbs_client = fbs_client

        self.add_nodes(self.input, self.fbs_client)

    def _process(self):
        ts, frame = self.input.read()

        if frame is None:
            return

        if isinstance(self.input, BaseDepthInput):
            # read depth map and create rgb-d
            depth_map = self.input.depth_map

            # resize to match rgb image if necessary
            if depth_map.shape != frame.shape:
                h, w = frame.shape[:2]
                depth_map = cv2.resize(depth_map, (w, h))

            rgbd = np.hstack((depth_map, frame))
        else:
            # just send rgb image for testing
            rgbd = frame

        # send rgb-d over spout
        bgrd = cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR)
        self.fbs_client.send(bgrd)

        # imshow does only work in main thread!
        if threading.current_thread() is threading.main_thread():
            cv2.imshow("RGB-D FrameBuffer Sharing Demo", rgbd)
            if cv2.waitKey(15) & 0xFF == 27:
                self.close()

    @staticmethod
    def add_params(parser: argparse.ArgumentParser):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RGB-D framebuffer sharing demo for visiongraph")
    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)
    args = parser.parse_args()

    if issubclass(args.input, RealSenseInput):
        # set realsense options
        args.depth = True
        args.color_scheme = RealSenseColorScheme.WhiteToBlack
        args.rs_filter = [rs.spatial_filter, rs.temporal_filter, rs.hole_filling_filter]

    # create frame buffer sharing client
    fbs_client = FrameBufferSharingClient.create("RGBDStream")

    # run pipeline
    pipeline = DemoPipeline(args.input(), fbs_client)
    pipeline.configure(args)
    pipeline.open()
