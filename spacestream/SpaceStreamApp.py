from typing import Optional

from visiongraph import vg
from visiongui.app.VisiongraphApp import VisiongraphApp

from spacestream.SpaceStreamConfig import SpaceStreamConfig
from spacestream.SpaceStreamGraph import SpaceStreamGraph


class SpaceStreamApp(VisiongraphApp[SpaceStreamGraph, SpaceStreamConfig]):

    def __init__(self, config: SpaceStreamConfig,
                 input_node: vg.BaseInput,
                 segnet: Optional[vg.InstanceSegmentationEstimator] = None,
                 fbs_server_type: vg.FrameBufferSharingServer = vg.FrameBufferSharingServer,
                 multi_threaded: bool = True):
        self.input_node = input_node
        self.segnet = segnet
        self.fbs_server_type = fbs_server_type
        self.multi_threaded = multi_threaded
        super().__init__(config)

    def create_graph(self) -> SpaceStreamGraph:
        graph = SpaceStreamGraph(self.config, self.input_node,
                                 segnet=self.segnet, fbs_server_type=self.fbs_server_type,
                                 multi_threaded=self.multi_threaded)
        return graph
