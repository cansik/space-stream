from argparse import ArgumentParser, Namespace
from typing import Optional

import cv2
import numpy as np
import visiongraph as vg


class ImageRectificationNode(vg.GraphNode[np.ndarray, np.ndarray]):

    def __init__(self, cam: vg.BaseCamera,
                 stream_type: vg.CameraStreamType = vg.CameraStreamType.Color,
                 interpolation_method: int = cv2.INTER_NEAREST):
        self.cam = cam
        self.stream_type = stream_type
        self.interpolation_method = interpolation_method

        self.map_x: Optional[np.ndarray] = None
        self.map_y: Optional[np.ndarray] = None

    def setup(self):
        pass

    def process(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]

        if self.map_x is None or self.map_y is None:
            self.calculate_map(w, h)

        rectified_image = cv2.remap(image, self.map_x, self.map_y, self.interpolation_method)
        return rectified_image

    def release(self):
        pass

    def calculate_map(self, width: int, height: int):
        size = (width, height)
        calib = self.cam.get_intrinsics(self.stream_type)

        # optimal mat not currently used
        # optimal_cam_mat, roi = cv2.getOptimalNewCameraMatrix(calib.intrinsic_matrix, calib.distortion_coefficients, size, 1, size)

        self.map_x, self.map_y = cv2.initUndistortRectifyMap(calib.intrinsic_matrix,
                                                             calib.distortion_coefficients,
                                                             None,
                                                             calib.intrinsic_matrix,
                                                             size,
                                                             5)

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass
