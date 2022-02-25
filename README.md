# Space Stream
Send RGB-D images over spout / syphon with visiongraph.

![Example Map](images/example.jpg)
*Source: Intel® RealSense™ [Sample Data](https://github.com/IntelRealSense/librealsense/blob/master/doc/sample-data.md)*

### Installation
It is recommended to use `Python 3.8` or higher and should run on any OS. First create a new [virtualenv](https://docs.python.org/3/library/venv.html) and activate it. 
After that install all dependencies:

```bash
pip install -r requirements.txt
```

### Usage
Simply run the `spacestream` module with the following command to run a capturing pipeline (RealSense based). After that you can open a [spout receiver](https://github.com/leadedge/Spout2/releases) / syphon receiver and check the result there.

```
python -m spacestream --input realsense
```

To use the Azure Kinect use the `azure` input type:

```
python -m spacestream --input azure
```

#### Depth Encoding
By default the depthmap is encoded by the realsense colorizer. It is possible to change the behaviour to use a specific encoding method. Be aware that some functions have an impact on performance because of the power calculation. Here is a list of all available:

```
Colorizer, Linear, Quad
```

To convert the `Quad` encoding back it is possible to use `1-sqrt(x)`.

And it is possible to set the specific encoding by using the `--depth-encoding` parameter or by using the number keys on the viewer (0 = Colorizer, 1 = Linear, ..).

```
python -m spacestream --input realsense --depth-encoding Quad
```

#### Bit Depth
By default the bit depth is 8bit, but it is also possible to change it to a 16 bit encoding where two color channels (blue, green) are used. Green for the most significant bits and blue for the least significant bits (little-endian).
To change the bit-depth use the parameter `--bit-depth` or the keyboard key `b` in the viewer:

```
python -m spacestream --input realsense --depth-encoding Quad --bit-depth 16
```

#### Distance Range
To define the min and max distance to encode, use the `--min-distance` and `--max-distance` parameter.

#### Help

```
usage: spacestream [-h] [-c CONFIG]
                   [--loglevel {critical,error,warning,info,debug}]
                   [--depth-encoding Colorizer,Linear,Quad]
                   [--min-distance MIN_DISTANCE] [--max-distance MAX_DISTANCE]
                   [--bit-depth {8,16}] [--stream-name STREAM_NAME]
                   [--input video-capture,image,realsense]
                   [--input-size width height] [--input-fps INPUT_FPS]
                   [--input-rotate 90,-90,180] [--input-flip h,v]
                   [--raw-input] [--channel CHANNEL] [--input-skip INPUT_SKIP]
                   [--input-path INPUT_PATH] [--input-delay INPUT_DELAY]
                   [--depth] [--depth-as-input] [-ir] [--exposure EXPOSURE]
                   [--gain GAIN] [--white-balance WHITE_BALANCE]
                   [--rs-serial RS_SERIAL] [--rs-json RS_JSON]
                   [--rs-play-bag RS_PLAY_BAG] [--rs-record-bag RS_RECORD_BAG]
                   [--rs-disable-emitter]
                   [--rs-filter decimation,spatial,temporal,hole-filling [decimation,spatial,temporal,hole-filling ...]]
                   [--rs-color-scheme Jet,Classic,WhiteToBlack,BlackToWhite,Bio,Cold,Warm,Quantized,Pattern]
                   [--midas] [--mask]
                   [--segnet mediapipe,mediapipe-light,mediapipe-heavy,maskrcnn,maskrcnn-eff-480,maskrcnn-eff-608,maskrcnn-res50-768,maskrcnn-res101-800]
                   [--no-filter] [--no-preview] [--record]

RGB-D framebuffer sharing demo for visiongraph

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Configuration file path.
  --loglevel {critical,error,warning,info,debug}
                        Provide logging level. Example --loglevel debug,
                        default=warning
  --depth-encoding Colorizer,Linear,Quad
                        Method how the depth map will be encoded, default:
                        Colorizer.
  --min-distance MIN_DISTANCE
                        Min distance to perceive by the camera.
  --max-distance MAX_DISTANCE
                        Max distance to perceive by the camera.
  --bit-depth {8,16}    Encoding output bit depth (default: 8).
  --stream-name STREAM_NAME
                        Spout / Syphon stream name.
  --segnet mediapipe,mediapipe-light,mediapipe-heavy,maskrcnn,maskrcnn-eff-480,maskrcnn-eff-608,maskrcnn-res50-768,maskrcnn-res101-800
                        Segmentation Network, default: mediapipe.

input provider:
  --input video-capture,image,realsense
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
  --input-path INPUT_PATH
                        Path to the input image.
  --input-delay INPUT_DELAY
                        Input delay time (s).
  --depth               Enable RealSense depth stream.
  --depth-as-input      Use colored depth stream as input stream.
  -ir, --infrared       Use infrared as input stream.
  --exposure EXPOSURE   Exposure value (usec) for depth camera input (disables
                        auto-exposure).
  --gain GAIN           Gain value for depth input (disables auto-exposure).
  --white-balance WHITE_BALANCE
                        White-Balance value for depth input (disables auto-
                        white-balance).
  --rs-serial RS_SERIAL
                        RealSense serial number to choose specific device.
  --rs-json RS_JSON     RealSense json configuration to apply.
  --rs-play-bag RS_PLAY_BAG
                        Path to a pre-recorded bag file for playback.
  --rs-record-bag RS_RECORD_BAG
                        Path to a bag file to store the current recording.
  --rs-disable-emitter  Disable RealSense IR emitter.
  --rs-filter decimation,spatial,temporal,hole-filling [decimation,spatial,temporal,hole-filling ...]
                        RealSense depth filter.
  --rs-color-scheme Jet,Classic,WhiteToBlack,BlackToWhite,Bio,Cold,Warm,Quantized,Pattern
                        Color scheme for depth map, default: WhiteToBlack.
  --midas               Use midas for depth capture.

masking:
  --mask                Apply mask by segmentation algorithm.

debug:
  --no-filter           Disable realsense image filter.
  --no-preview          Disable preview to speed.
  --record              Record output into recordings folder.
```

### About
Copyright (c) 2022 Florian Bruggisser