from typing import Optional

from visiongui.app.VisiongraphApp import VisiongraphApp

from spacestream.SpaceStreamConfig import SpaceStreamConfig
from spacestream.SpaceStreamGraph import SpaceStreamGraph

import visiongraph as vg


class SpaceStreamApp(VisiongraphApp[SpaceStreamGraph, SpaceStreamConfig]):

    def __init__(self, config: SpaceStreamConfig,
                 input_node: vg.BaseInput,
                 segnet: Optional[vg.InstanceSegmentationEstimator] = None,
                 multi_threaded: bool = True):
        self.input_node = input_node
        self.segnet = segnet
        self.multi_threaded = multi_threaded
        super().__init__(config)

    def create_graph(self) -> SpaceStreamGraph:
        graph = SpaceStreamGraph(self.config, self.input_node,
                                 segnet=self.segnet, multi_threaded=self.multi_threaded)
        return graph
