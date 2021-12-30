import argparse
import logging
import threading
from typing import Optional

import SpoutGL
import cv2
import numpy as np
import pyrealsense2 as rs
from OpenGL import GL
from visiongraph.Pipeline import Pipeline
from visiongraph.input import RealSenseInput, add_input_step_choices
from visiongraph.model.types.RealSenseColorScheme import RealSenseColorScheme


class DemoPipeline(Pipeline):

    def __init__(self, input: RealSenseInput, multi_threaded: bool = False, deamon: bool = False):
        super().__init__(multi_threaded, deamon)
        self.input = input

        self.spout_name = "RGBDStream"
        self.spout: Optional[SpoutGL.SpoutSender] = None

        self.add_nodes(self.input)

    def _init(self):
        super()._init()

        # setup spout
        self.spout = SpoutGL.SpoutSender()
        self.spout.setSenderName(self.spout_name)

    def _process(self):
        ts, frame = self.input.read()

        if frame is None:
            return

        # read depth map and create rgb-d
        depth_map = self.input.depth_map
        rgbd = np.hstack((depth_map, frame))

        # send rgb-d over spout
        h, w = rgbd.shape[:2]
        bgrd = cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR)
        success = self.spout.sendImage(bgrd, w, h, GL.GL_RGB, False, 0)
        if not success:
            logging.warning("Could not send spout image.")

        # Indicate that a frame is ready to read
        self.spout.setFrameSync(self.spout_name)

        # imshow does not work in thread!
        if threading.current_thread() is threading.main_thread():
            cv2.imshow("Spout Demo", rgbd)
            if cv2.waitKey(15) & 0xFF == 27:
                self.close()

    def _release(self):
        super()._release()
        self.spout.releaseSender()

    @staticmethod
    def add_params(parser: argparse.ArgumentParser):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Spout demo for visiongraph")
    input_group = parser.add_argument_group("input provider")
    add_input_step_choices(input_group)
    args = parser.parse_args()

    args.input = RealSenseInput
    args.depth = True
    args.color_scheme = RealSenseColorScheme.WhiteToBlack
    args.rs_filter = [rs.spatial_filter, rs.temporal_filter, rs.hole_filling_filter]

    # run pipeline
    pipeline = DemoPipeline(args.input())
    pipeline.configure(args)
    pipeline.open()
