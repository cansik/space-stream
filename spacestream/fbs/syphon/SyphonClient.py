import logging
from argparse import ArgumentParser, Namespace
from typing import Sequence, Optional, Tuple

import numpy as np
import syphonpy

from spacestream.fbs.FrameBufferSharingClient import FrameBufferSharingClient
from spacestream.fbs.syphon import SyphonUtils


class SyphonClient(FrameBufferSharingClient):
    def __init__(self, server_name: str, create_gl_context: bool = True):
        super().__init__(server_name)

        self.ctx: Optional[syphonpy.SyphonClient] = None

        self.create_gl_context = create_gl_context
        self._window_handle: Optional[int] = None

    def setup(self):
        # setup GL context
        if self.create_gl_context:
            self._window_handle = SyphonUtils.create_gl_context()

        # setup syphon
        if self.server_name != "":
            self.select_server(self.server_name)

    def receive_frame(self) -> np.array:
        pass

    def receive_texture(self, texture_handle: int):
        if self.ctx.has_new_frame():
            print("new frame available")

        img = self.ctx.new_frame_image()

        if self.ctx.error_state():
            print("there is an error")

        if not self.ctx.is_valid():
            print("is not valid")

        size = img.texture_size()

        name = img.texture_name()
        width = size.width
        height = size.height

        print(f"Name {name}, {width}x{height}")

    def release(self):
        self.ctx.stop()
        SyphonUtils.release_gl_context(self._window_handle)

    def get_available_servers(self) -> Sequence[str]:
        servers = syphonpy.ServerDirectory.servers()

        server_list = []
        for s in servers:
            if s.name == "":
                server_name = s.app_name
            else:
                server_name = f"{s.app_name}:{s.name}"
            server_list.append(server_name)

        return server_list

    def select_server(self, server_name: str):
        if ":" in server_name:
            app_name, s_name = server_name.split(":")
        else:
            app_name, s_name = server_name, ""

        servers = syphonpy.ServerDirectory.servers()
        valid_servers = [s for s in servers if s.app_name == app_name and s.name == s_name]

        if len(valid_servers) == 0:
            raise Exception(f"Server {server_name} has not been found.")

        server_description = valid_servers[0]

        if self.ctx is not None:
            self.ctx.stop()

        self.ctx = syphonpy.SyphonClient(server_description)
        if self.ctx.error_state():
            logging.error("error in syphon client")

        self.server_name = server_name

    def configure(self, args: Namespace):
        pass

    @staticmethod
    def add_params(parser: ArgumentParser):
        pass
