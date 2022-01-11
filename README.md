# Spout & Syphon RGB-D Example
An example which streams RGB-D images over spout / syphon with visiongraph.

### Installation
It is recommended to use `Python 3.8` or higher and should run on any OS. First create a new [virtualenv](https://docs.python.org/3/library/venv.html) and activate it. 
After that install all dependencies:

```bash
# on MacOS use this:
pip install -r requirements-macos.txt

# on Windows use this:
pip install -r requirements-windows.txt
```

### Usage
Simply run the [demo.py](demo.py) with the following command to run a capturing pipeline (RealSense based). After that you can open a [spout receiver](https://github.com/leadedge/Spout2/releases) and check the result there.

```
python demo.py --realsense
```

#### Help

```
usage: demo.py [-h] [--input video-capture,realsense]
               [--input-size width height] [--input-fps INPUT_FPS]
               [--input-rotate 90,-90,180] [--input-flip h,v] [--raw-input]
               [--channel CHANNEL] [--input-skip INPUT_SKIP] [-ir]
               [--exposure EXPOSURE] [--gain GAIN] [--rs-serial RS_SERIAL]
               [--disable-emitter] [--depth]
               [--rs-filter decimation,spatial,temporal,hole-filling [decimation,spatial,temporal,hole-filling ...]]
               [--depth-as-input]
               [--color-scheme Jet,Classic,WhiteToBlack,BlackToWhite,Bio,Cold,Warm,Quantized,Pattern]

Spout demo for visiongraph

optional arguments:
  -h, --help            show this help message and exit

input provider:
  --input video-capture,realsense
                        Image input provider, default: video-capture.
  --input-size width height
                        Requested input media size.
  --input-fps INPUT_FPS
                        Requested input media framerate.
  --input-rotate 90,-90,180
                        Rotate input media.
  --input-flip h,v      Flip input media.
  --raw-input           Skip automatic input conversion to 3-channel image.
  --channel CHANNEL     Input device channel (camera id, video path, image
                        sequence).
  --input-skip INPUT_SKIP
                        If set the input will be skipped to the value in
                        milliseconds.
  -ir, --infrared       Use infrared as input stream (RealSense).
  --exposure EXPOSURE   Exposure value (usec) for realsense input (disables
                        auto-exposure).
  --gain GAIN           Gain value for realsense input (disables auto-
                        exposure).
  --rs-serial RS_SERIAL
                        RealSense serial number to choose specific device.
  --disable-emitter     Disable RealSense IR emitter.
  --depth               Enable RealSense depth stream.
  --rs-filter decimation,spatial,temporal,hole-filling [decimation,spatial,temporal,hole-filling ...]
                        RealSense depth filter.
  --depth-as-input      Use colored depth stream as input stream.
  --color-scheme Jet,Classic,WhiteToBlack,BlackToWhite,Bio,Cold,Warm,Quantized,Pattern
                        Color scheme for depth map, default: WhiteToBlack.
```

### About
Copyright (c) 2021 Florian Bruggisser