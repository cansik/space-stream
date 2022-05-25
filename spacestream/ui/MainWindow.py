import logging
import signal
import traceback
from typing import Optional, Sequence

import cv2
import numpy as np
import open3d as o3d
from open3d.visualization import gui
from duit.ui.open3d.Open3dPropertyRegistry import init_open3d_registry
from duit.ui.open3d.PropertyPanel import PropertyPanel

from spacestream.SpaceStreamPipeline import SpaceStreamPipeline
from spacestream.codec.LinearCodec import LinearCodec
from spacestream.ui.PipelineView import PipelineView

import visiongraph as vg
import pyrealsense2 as rs


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
        self.settings_panel = PropertyPanel()
        self.settings_panel.data_context = pipeline
        self.window.add_child(self.settings_panel)

        # used for colorized preview
        self.colorizer = rs.colorizer()
        self.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)
        self.colorizer.set_option(rs.option.color_scheme, 9.0)
        self.colorizer.set_option(rs.option.min_distance, self.pipeline.min_distance.value)
        self.colorizer.set_option(rs.option.max_distance, self.pipeline.max_distance.value)

        # info panel
        self.settings_panel.add_child(gui.Label("View Parameter"))

        self.display_depth_map = gui.Checkbox("Display Depth Map")
        self.display_depth_map.checked = False
        self.settings_panel.add_child(self.display_depth_map)

        if args.view_3d:
            self.display_16_bit = gui.Checkbox("Display 16bit")
            self.display_16_bit.checked = True
            self.settings_panel.add_child(self.display_16_bit)

            self.render_3d_view = gui.Checkbox("Render 3D")
            self.render_3d_view.checked = True
            self.settings_panel.add_child(self.render_3d_view)

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

        if isinstance(pipeline.input, vg.RealSenseInput) and pipeline.input.input_bag_file is not None:
            self.settings_panel.add_child(gui.Label("RealSense"))

            self.play_bag = gui.Checkbox("Play")
            self.play_bag.checked = True
            self.settings_panel.add_child(self.play_bag)

            def on_play_bag_changed(value):
                if not isinstance(pipeline.input, vg.RealSenseInput):
                    return

                if pipeline.input.device is None:
                    return

                playback: rs.playback = pipeline.input.profile.get_device().as_playback()

                if value:
                    playback.resume()
                else:
                    playback.pause()

            self.play_bag.set_on_checked(on_play_bag_changed)

        separation_height = int(round(0.5 * self.em))

        self.none_image = o3d.geometry.Image(np.zeros(shape=(1, 1, 3), dtype="uint8"))

        # preview
        self.rgb_widget = gui.ImageWidget(self.none_image)
        self.window.add_child(self.rgb_widget)

        # hook to events
        self.pipeline.on_frame_ready = self.on_frame_ready
        self.pipeline.on_exception = self._on_pipeline_exception
        self.pipeline.disable_preview.on_changed += self._disable_preview_changed
        self.pipeline.disable_preview.fire_latest()

        signal.signal(signal.SIGINT, self._signal_handler)

        # pipeline
        self.pipeline_view: Optional[PipelineView] = None

        if args.view_3d:
            self.pipeline_view = PipelineView(60, 640 * 480, self.window, on_window_close=self._on_close)
            self.pipeline_view.window = self.window
            self.window.add_child(self.pipeline_view.pcdview)

        self.restart_pipeline_button = gui.Button("Restart Pipeline")
        self.restart_pipeline_button.set_on_clicked(self._on_restart_clicked)
        self.settings_panel.add_child(self.restart_pipeline_button)
        self.window.add_child(self.settings_panel)

        # start pipeline
        pipeline.fbs_client.setup()
        pipeline.open()

    def _signal_handler(self, signal, frame):
        self.window.close()

    def _on_restart_clicked(self):
        self.pipeline.close()
        self.pipeline.fbs_client.release()

        self.pipeline.fbs_client.setup()
        self.pipeline.open()

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

    @staticmethod
    def _create_preview_parameter(name: str, value: str) -> gui.Horiz:
        container = gui.Horiz()

        container.add_child(gui.Label(name))
        value_edit = gui.TextEdit()
        value_edit.text_value = value
        container.add_child(value_edit)

        def on_value_changed(text):
            value_edit.text_value = value

        value_edit.set_on_text_changed(on_value_changed)

        return container

    def on_frame_ready(self, frame: np.ndarray):
        bgrd = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        preview_image = bgrd

        if self.display_depth_map.checked:
            if isinstance(self.pipeline.input, vg.DepthBuffer):
                if isinstance(self.pipeline.input, vg.RealSenseInput):
                    self.colorizer.set_option(rs.option.min_distance, self.pipeline.min_distance.value)
                    self.colorizer.set_option(rs.option.max_distance, self.pipeline.max_distance.value)
                    colorized_frame = self.colorizer.colorize(self.pipeline.input.depth_frame)
                    preview_image = np.asanyarray(colorized_frame.get_data())
                else:
                    preview_image = self.pipeline.input.depth_map

        image = o3d.geometry.Image(preview_image)

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
        if not isinstance(self.pipeline.input, vg.BaseDepthCamera):
            return

        h, tw = frame.shape[:2]
        w = tw // 2

        # settings
        # read necessary data for visualisation
        extrinsics = o3d.core.Tensor.eye(4, dtype=o3d.core.Dtype.Float32)

        intrinsic_matrix = o3d.core.Tensor(
            self.pipeline.input.camera_matrix,
            dtype=o3d.core.Dtype.Float32)
        depth_max = self.pipeline.max_distance.value  # m
        pcd_stride = self.pcl_stride.int_value  # downsample point cloud, may increase frame rate
        flag_normals = False
        depth_scale = 1000

        # split image / and visualise
        color = np.copy(frame[0:h, w:w + w])
        depth = np.copy(frame[0:h, 0:w])

        # decode
        min_value = round(self.pipeline.min_distance.value / self.pipeline.depth_units)
        max_value = round(self.pipeline.max_distance.value / self.pipeline.depth_units)

        if isinstance(self.pipeline.depth_codec, LinearCodec):
            depth = self.pipeline.depth_codec.decode(depth, min_value, max_value,
                                                     decode_8bit=not self.display_16_bit.checked)
        else:
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

    def _disable_preview_changed(self, is_disabled: bool):
        if is_disabled:
            self.display_info("Preview Disabled")

    def display_info(self, text: str,
                     text_color: Sequence[int] = (255, 255, 255),
                     background_color: Sequence[int] = (0, 0, 0)):
        img = np.zeros((512, 512, 3), np.uint8)
        img[:, :] = background_color

        # setup text
        font = cv2.FONT_HERSHEY_SIMPLEX

        # get boundary of this text
        text_size = cv2.getTextSize(text, font, 1, 2)[0]

        # get coords based on boundary
        text_x = (img.shape[1] - text_size[0]) // 2
        text_y = (img.shape[0] + text_size[1]) // 2

        # add text centered on image
        cv2.putText(img, text, (text_x, text_y), font, 1, text_color, 2)

        image = o3d.geometry.Image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        def update():
            self.rgb_widget.update_image(image)

        gui.Application.instance.post_to_main_thread(self.window, update)
