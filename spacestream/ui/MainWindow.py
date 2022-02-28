import logging
import signal
import traceback
from typing import Optional

import cv2
import numpy as np
import open3d as o3d
from open3d.visualization import gui, rendering

from spacestream.SpaceStreamPipeline import SpaceStreamPipeline
from spacestream.ui.PipelineView import PipelineView


class MainWindow:
    def __init__(self, pipeline: SpaceStreamPipeline):
        self.pipeline = pipeline

        self.window: gui.Window = gui.Application.instance.create_window(pipeline.stream_name,
                                                                         round(1000),
                                                                         round(800))
        self.window.set_on_layout(self._on_layout)
        self.window.set_on_close(self._on_close)

        self.em = self.window.theme.font_size
        margin = 0.5 * self.em

        self.settings_panel_width = 18 * self.em  # 15 ems wide

        separation_height = int(round(0.5 * self.em))

        self.none_image = o3d.geometry.Image(np.zeros(shape=(1, 1, 3), dtype="uint8"))

        # preview
        self.rgb_widget = gui.ImageWidget(self.none_image)
        self.window.add_child(self.rgb_widget)

        # hook to events
        self.pipeline.on_frame_ready = self.on_frame_ready
        self.pipeline.on_exception = self._on_pipeline_exception

        signal.signal(signal.SIGINT, self._signal_handler)

        # pipeline
        self.pipeline_view = PipelineView(
            60,
            640 * 480,
            on_window_close=self._on_close)

        # start pipeline
        pipeline.fbs_client.setup()
        pipeline.open()

    def _signal_handler(self, signal, frame):
        self.window.close()

    def _on_pipeline_exception(self, pipeline, ex):
        # display error message in console
        logging.warning("".join(traceback.TracebackException.from_exception(ex).format()))

    def _on_layout(self, layout_context):
        content_rect = self.window.content_rect
        self.rgb_widget.frame = gui.Rect(content_rect.x, content_rect.y,
                                         content_rect.width,
                                         content_rect.height)

    def _on_close(self):
        self.pipeline.fbs_client.release()
        self.pipeline.close()
        gui.Application.instance.quit()

    def on_frame_ready(self, frame: np.ndarray):
        bgrd = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        image = o3d.geometry.Image(bgrd)

        h, tw = bgrd.shape[:2]
        w = tw // 2
        self.pipeline_view.max_pcd_vertices = h * w

        self.create_3d_cloud(bgrd)

        def update():
            # send stream
            self.pipeline.fbs_client.send(bgrd)

            # update image
            self.rgb_widget.update_image(image)

        gui.Application.instance.post_to_main_thread(self.window, update)

    def create_3d_cloud(self, frame):
        h, tw = frame.shape[:2]
        w = tw // 2

        # settings
        # read necessary data for visualisation
        extrinsics = o3d.core.Tensor.eye(4, dtype=o3d.core.Dtype.Float32)
        intrinsic_matrix = o3d.core.Tensor(
            self.pipeline.get_intrinsics(),
            dtype=o3d.core.Dtype.Float32)
        depth_max = 6.0  # m
        pcd_stride = 2  # downsample point cloud, may increase frame rate
        flag_normals = False
        depth_scale = 1000

        # split image
        depth = (np.copy(frame[0:h, 0:w]) * 255).astype(np.uint16)
        color = np.copy(frame[0:h, w:w + w])

        color_frame = o3d.t.geometry.Image(color)
        depth_frame = o3d.t.geometry.Image(depth)

        rgbd_image = o3d.t.geometry.RGBDImage(color_frame, depth_frame, True)
        pcd = o3d.t.geometry.PointCloud.create_from_rgbd_image(rgbd_image, intrinsic_matrix, extrinsics,
                                                               depth_scale, depth_max,
                                                               pcd_stride, flag_normals)

        o3d.t.io.write_point_cloud("test.ply", pcd)

        frame_elements = {
            'color': None,
            'depth': None,
            'pcd': pcd,
            'status_message': ""
        }

        def update():
            self.pipeline_view.update(frame_elements)

        gui.Application.instance.post_to_main_thread(self.pipeline_view.window, update)
