import logging
import signal
import traceback
from typing import Optional

import cv2
import numpy as np
import open3d as o3d
from open3d.visualization import gui
from simbi.ui.open3d.Open3dPropertyRegistry import init_open3d_registry
from simbi.ui.open3d.PropertyPanel import PropertyPanel

from spacestream.SpaceStreamPipeline import SpaceStreamPipeline
from spacestream.ui.PipelineView import PipelineView


class MainWindow:
    def __init__(self, pipeline: SpaceStreamPipeline, args):
        self.pipeline = pipeline
        init_open3d_registry()

        self.window: gui.Window = gui.Application.instance.create_window(f"Space Stream - {pipeline.stream_name}",
                                                                         round(1000),
                                                                         round(800))
        self.window.set_on_layout(self._on_layout)
        self.window.set_on_close(self._on_close)

        self.em = self.window.theme.font_size
        margin = 0.5 * self.em

        # settings panel
        self.settings_panel_width = 18 * self.em  # 15 ems wide
        self.settings_panel = PropertyPanel(0, gui.Margins(0.25 * self.em))
        self.settings_panel.data_context = pipeline
        self.window.add_child(self.settings_panel)

        self.settings_panel.add_child(gui.Label("View Parameter"))
        self.render_3d_view = gui.Checkbox("Render 3D")
        self.render_3d_view.checked = True
        self.settings_panel.add_child(self.render_3d_view)

        self.display_16_bit = gui.Checkbox("Display 16bit")
        self.settings_panel.add_child(self.display_16_bit)

        self.settings_panel.add_child(gui.Label("PCL Stride"))
        self.pcl_stride = gui.Slider(gui.Slider.INT)
        self.pcl_stride.set_limits(1, 10)
        self.pcl_stride.int_value = 4
        self.settings_panel.add_child(self.pcl_stride)

        self.settings_panel.add_child(gui.Label("Point Size"))
        self.point_size = gui.Slider(gui.Slider.INT)
        self.point_size.set_limits(1, 10)
        self.point_size.int_value = 2
        self.settings_panel.add_child(self.point_size)

        def on_point_size_changed(size):
            if self.pipeline_view is None:
                return
            self.pipeline_view.pcd_material.point_size = int(size * self.window.scaling)

        self.point_size.set_on_value_changed(on_point_size_changed)

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
        self.pipeline_view: Optional[PipelineView] = None

        if args.view_pcd:
            self.pipeline_view = PipelineView(60, 640 * 480, self.window, on_window_close=self._on_close)
            self.pipeline_view.window = self.window
            self.window.add_child(self.pipeline_view.pcdview)

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
        pcb_view_height = 0

        if self.pipeline_view is not None:
            pcb_view_height = content_rect.height // 2

            self.pipeline_view.pcdview.frame = gui.Rect(content_rect.x, content_rect.y,
                                                        content_rect.width - self.settings_panel_width,
                                                        pcb_view_height)

        self.rgb_widget.frame = gui.Rect(content_rect.x, pcb_view_height,
                                         content_rect.width - self.settings_panel_width,
                                         content_rect.height - pcb_view_height)

        self.settings_panel.frame = gui.Rect(self.rgb_widget.frame.get_right(),
                                             content_rect.y, self.settings_panel_width,
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

        if self.pipeline_view is not None and self.render_3d_view.checked:
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
        depth_max = self.pipeline.max_distance  # m
        pcd_stride = self.pcl_stride.int_value  # downsample point cloud, may increase frame rate
        flag_normals = False
        depth_scale = 1000

        # split image / and visualise
        color = np.copy(frame[0:h, w:w + w])
        depth = np.copy(frame[0:h, 0:w])

        # decode
        min_value = round(self.pipeline.min_distance / self.pipeline.depth_units)
        max_value = round(self.pipeline.max_distance / self.pipeline.depth_units)
        depth = self.pipeline.depth_codec.decode(depth, min_value, max_value)

        depth = cv2.cvtColor(depth, cv2.COLOR_GRAY2RGB)

        color_frame = o3d.t.geometry.Image(color)
        depth_frame = o3d.t.geometry.Image(depth)

        rgbd_image = o3d.t.geometry.RGBDImage(color_frame, depth_frame, True)
        pcd = o3d.t.geometry.PointCloud.create_from_rgbd_image(rgbd_image, intrinsic_matrix, extrinsics,
                                                               depth_scale, depth_max,
                                                               pcd_stride, flag_normals)

        frame_elements = {
            'color': None,
            'depth': None,
            'pcd': pcd,
            'status_message': ""
        }

        def update():
            self.pipeline_view.update(frame_elements)

        gui.Application.instance.post_to_main_thread(self.pipeline_view.window, update)
