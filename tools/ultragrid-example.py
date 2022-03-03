import argparse
import os
from io import BufferedWriter
from typing import Optional

import cv2
import numpy as np
import visiongraph as vg

uv_pipe: Optional[BufferedWriter] = None


def on_frame_ready(frame: np.ndarray):
    # pipe frame
    _, encoded = cv2.imencode('.bmp', frame)

    if uv_pipe is not None:
        uv_pipe.write(encoded.tobytes())

    return frame


def main():
    pipeline = vg.create_graph(name="Ultragrid Example", handle_signals=True) \
        .then(vg.custom(on_frame_ready), vg.ImagePreview()) \
        .build()
    pipeline.configure(args)

    # create pipe
    try:
        os.mkfifo(args.pipe)
    except OSError as e:
        print(f"Failed to create FIFO: {e}")

    global uv_pipe
    print(f"Pipe:\n{os.path.abspath(args.pipe)}")
    uv_pipe = open(args.pipe, "wb")

    pipeline.open()
    pipeline.close()
    uv_pipe.close()
    os.remove(args.pipe)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("VisionGraph to Ultragrid", description="Example Pipeline")
    parser.add_argument("--pipe", type=str, default="uvpipe", help="Named pipe name.")
    vg.VisionGraph.add_params(parser)
    args = parser.parse_args()

    main()
