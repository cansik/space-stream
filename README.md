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

#### Depth Codec
By default the depthmap is encoded by the linear codec. It is possible to change the behaviour to use a specific encoding method. Be aware that some functions have an impact on performance. Here is a list of all available codecs:

```
Linear,
UniformHue
InverseHue
```

The codecs `UniformHue` and `InverseHue` are implemented according to the Intel whitepaper about [Depth image compression by colorization](https://dev.intelrealsense.com/docs/depth-image-compression-by-colorization-for-intel-realsense-depth-cameras).

#### Bit Depth
The encoded bit-depth depends on the codec used. For `Linear` codec there are two different bit-depths encoded. First the `8-bit` encoding in the `red` channel and `16-bit` encoded values in the `green` (MSB) and `blue` (LSB) channel.

#### Distance Range
To define the min and max distance to encode, use the `--min-distance` and `--max-distance` parameter.

#### Help

```
usage: spacestream [-h] [-c CONFIG]
                   [--loglevel {critical,error,warning,info,debug}]
                   [--input video-capture,image,realsense,azure]
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
                   [--k4a-align] [--k4a-device K4A_DEVICE]
                   [--k4a-play-mkv K4A_PLAY_MKV]
                   [--k4a-record-mkv K4A_RECORD_MKV]
                   [--k4a-depth-mode OFF,NFOV_2X2BINNED,NFOV_UNBINNED,WFOV_2X2BINNED,WFOV_UNBINNED,PASSIVE_IR]
                   [--k4a-color-resolution OFF,RES_720P,RES_1080P,RES_1440P,RES_1536P,RES_2160P,RES_3072P]
                   [--k4a-color-format COLOR_MJPG,COLOR_NV12,COLOR_YUY2,COLOR_BGRA32,DEPTH16,IR16,CUSTOM8,CUSTOM16,CUSTOM]
                   [--midas] [--mask]
                   [--segnet mediapipe,mediapipe-light,mediapipe-heavy,maskrcnn,maskrcnn-eff-480,maskrcnn-eff-608,maskrcnn-res50-768,maskrcnn-res101-800]
                   [--codec Linear,UniformHue,InverseHue]
                   [--min-distance MIN_DISTANCE] [--max-distance MAX_DISTANCE]
                   [--no-parallel] [--no-fastmath] [--stream-name STREAM_NAME]
                   [--no-filter] [--no-preview] [--record] [--view-pcd]

RGB-D framebuffer sharing demo for visiongraph.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Configuration file path.
  --loglevel {critical,error,warning,info,debug}
                        Provide logging level. Example --loglevel debug,
                        default=warning

input provider:
  --input video-capture,image,realsense,azure
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
  --k4a-align           Align azure frames to depth frame.
  --k4a-device K4A_DEVICE
                        Azure device id.
  --k4a-play-mkv K4A_PLAY_MKV
                        Path to a pre-recorded bag file for playback.
  --k4a-record-mkv K4A_RECORD_MKV
                        Path to a mkv file to store the current recording.
  --k4a-depth-mode OFF,NFOV_2X2BINNED,NFOV_UNBINNED,WFOV_2X2BINNED,WFOV_UNBINNED,PASSIVE_IR
                        Azure depth mode, default: NFOV_UNBINNED.
  --k4a-color-resolution OFF,RES_720P,RES_1080P,RES_1440P,RES_1536P,RES_2160P,RES_3072P
                        Azure color resolution (overwrites input-size),
                        default: RES_720P.
  --k4a-color-format COLOR_MJPG,COLOR_NV12,COLOR_YUY2,COLOR_BGRA32,DEPTH16,IR16,CUSTOM8,CUSTOM16,CUSTOM
                        Azure color image format, default: COLOR_BGRA32.
  --midas               Use midas for depth capture.

masking:
  --mask                Apply mask by segmentation algorithm.
  --segnet mediapipe,mediapipe-light,mediapipe-heavy,maskrcnn,maskrcnn-eff-480,maskrcnn-eff-608,maskrcnn-res50-768,maskrcnn-res101-800
                        Segmentation Network, default: mediapipe.

depth codec:
  --codec Linear,UniformHue,InverseHue
                        Codec how the depth map will be encoded., default:
                        Linear.
  --min-distance MIN_DISTANCE
                        Min distance to perceive by the camera.
  --max-distance MAX_DISTANCE
                        Max distance to perceive by the camera.

performance:
  --no-parallel         Disable parallel for codec operations.
  --no-fastmath         Disable fastmath for codec operations.

output:
  --stream-name STREAM_NAME
                        Spout / Syphon stream name.

debug:
  --no-filter           Disable realsense image filter.
  --no-preview          Disable preview to speed.
  --record              Record output into recordings folder.
  --view-pcd            Display PCB preview.
```

### About
Copyright (c) 2022 Florian Bruggisser