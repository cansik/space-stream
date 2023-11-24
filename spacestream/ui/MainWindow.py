import logging
import signal
import traceback
from typing import Sequence

import cv2
import numpy as np
import open3d as o3d
import pyrealsense2 as rs
import visiongraph as vg
from open3d.visualization import gui
from visiongui.ui.VisiongraphUserInterface import VisiongraphUserInterface

from spacestream.SpaceStreamApp import SpaceStreamApp
from spacestream.SpaceStreamConfig import SpaceStreamConfig
from spacestream.WatchDog import HealthStatus, WatchDog


class MainWindow(VisiongraphUserInterface[SpaceStreamApp, SpaceStreamConfig]):
    def __init__(self, app: SpaceStreamApp):
        super().__init__(app, width=1000, height=800, handle_graph_state=True)

        def on_stream_name_changed(new_stream_name: str):
            self.window.title = f"SpaceStream - {new_stream_name}"

        self.config.stream_name.on_changed += on_stream_name_changed
        self.config.stream_name.fire_latest()

        # used for colorized preview
        self.colorizer = rs.colorizer()
        self.colorizer.set_option(rs.option.histogram_equalization_enabled, 0)
        self.colorizer.set_option(rs.option.color_scheme, 9.0)
        self.colorizer.set_option(rs.option.min_distance, self.config.min_distance.value)
        self.colorizer.set_option(rs.option.max_distance, self.config.max_distance.value)

        if isinstance(self.graph.input, vg.RealSenseInput) and self.graph.input.input_bag_file is not None:
            self.settings_panel.add_child(gui.Label("RealSense"))

            self.play_bag = gui.Checkbox("Play")
            self.play_bag.checked = True
            self.settings_panel.add_child(self.play_bag)

            def on_play_bag_changed(value):
                if not isinstance(self.graph.input, vg.RealSenseInput):
                    return

                if self.graph.device is None:
                    return

                playback: rs.playback = self.graph.input.profile.get_device().as_playback()

                if value:
                    playback.resume()
                else:
                    playback.pause()

            self.play_bag.set_on_checked(on_play_bag_changed)

        separation_height = int(round(0.5 * self.em))

        self.none_image = o3d.geometry.Image(np.zeros(shape=(1, 1, 3), dtype="uint8"))

        # hook to events
        self.graph.on_frame_ready = self.on_frame_ready
        self.graph.on_exception = self._on_pipeline_exception

        self.config.disable_preview.on_changed += self._disable_preview_changed
        self.config.disable_preview.fire_latest()

        signal.signal(signal.SIGINT, self._signal_handler)

        self.restart_pipeline_button = gui.Button("Restart Pipeline")
        self.restart_pipeline_button.set_on_clicked(self._on_restart_clicked)
        self.settings_panel.add_child(self.restart_pipeline_button)

        # graph indicator
        self.graph_indicator = gui.Horiz(margins=gui.Margins(8, 8, 8, 8))
        self.graph_indicator.add_stretch()
        self.indicator_label = gui.Label("Starting up...")
        self.graph_indicator.add_child(self.indicator_label)
        self.graph_indicator.add_stretch()

        self.online_color = gui.Color(0.2, 0.6, 0.2, 1.0)
        self.warning_color = gui.Color(0.6, 0.6, 0.2, 1.0)
        self.offline_color = gui.Color(0.6, 0.2, 0.2, 1.0)

        self.indicator_size = self.em * 2
        self.window.add_child(self.graph_indicator)

        self.watch_dog = WatchDog()
        self.watch_dog.health.on_changed += self._on_health_update

        self.window.set_on_tick_event(self._on_tick)

    def _on_health_update(self, status: HealthStatus):
        logging.warning(f"Health changed to: {status.name}")

        def _update():
            self.indicator_label.text = status.name

            if status == HealthStatus.Online:
                self.graph_indicator.background_color = self.online_color
            elif status == HealthStatus.Warning:
                self.graph_indicator.background_color = self.warning_color
            elif status == HealthStatus.Offline:
                self.graph_indicator.background_color = self.offline_color

        self.invoke_on_gui(_update)

    def _on_tick(self) -> bool:
        self.watch_dog.update()
        return True

    def _on_layout(self, layout_context: gui.LayoutContext):
        content_rect = self.window.content_rect

        self.graph_indicator.frame = gui.Rect(content_rect.x, content_rect.y,
                                              content_rect.width - self.settings_panel_width,
                                              self.indicator_size)

        self.image_view.frame = gui.Rect(content_rect.x, content_rect.y + self.indicator_size,
                                         content_rect.width - self.settings_panel_width,
                                         content_rect.height)

        self.settings_panel.frame = gui.Rect(self.image_view.frame.get_right(),
                                             content_rect.y, self.settings_panel_width,
                                             content_rect.height)

    def _signal_handler(self, signal, frame):
        self.window.close()

    def _on_restart_clicked(self):
        self.graph.close()
        self.graph.open()

    def _on_pipeline_exception(self, pipeline, ex):
        # display error message in console
        logging.warning("".join(traceback.TracebackException.from_exception(ex).format()))

    def _on_layout_unused(self, layout_context):
        content_rect = self.window.content_rect
        pcb_view_height = 0

        if self.pipeline_view is not None:
            pcb_view_height = content_rect.height // 2

            self.pipeline_view.pcdview.frame = gui.Rect(content_rect.x, content_rect.y,
                                                        content_rect.width - self.settings_panel_width,
                                                        pcb_view_height)

        self.image_view.frame = gui.Rect(content_rect.x, pcb_view_height,
                                         content_rect.width - self.settings_panel_width,
                                         content_rect.height - pcb_view_height)

        self.settings_panel.frame = gui.Rect(self.image_view.frame.get_right(),
                                             content_rect.y, self.settings_panel_width,
                                             content_rect.height)

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
        self.watch_dog.reset()

        if self.config.disable_preview.value:
            return

        bgrd = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        preview_image = bgrd

        if self.config.display_vertical_stack.value:
            h, w = preview_image.shape[:2]
            hw = w // 2
            depth_roi = preview_image[0:h, 0:hw]
            color_roi = preview_image[0:h, hw:w]
            preview_image = np.vstack((color_roi, depth_roi))

        if self.config.display_depth_map.value:
            if isinstance(self.graph.input, vg.DepthBuffer):
                if isinstance(self.graph.input, vg.RealSenseInput):
                    self.colorizer.set_option(rs.option.min_distance, self.config.min_distance.value)
                    self.colorizer.set_option(rs.option.max_distance, self.config.max_distance.value)
                    colorized_frame = self.colorizer.colorize(self.graph.input.depth_frame)
                    preview_image = np.asanyarray(colorized_frame.get_data())
                else:
                    preview_image = self.graph.input.depth_map

        if self.config.record.value:
            preview_image = preview_image.copy()
            h, w = preview_image.shape[:2]
            cv2.circle(preview_image, (w - 25, 25), 15, (255, 0, 0), -1)

        image = o3d.geometry.Image(preview_image)

        def update():
            # send stream
            self.graph.fbs_client.send(bgrd)

            # update image
            self.image_view.update_image(image)

        gui.Application.instance.post_to_main_thread(self.window, update)

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
            self.image_view.update_image(image)

        gui.Application.instance.post_to_main_thread(self.window, update)
