import pyrealsense2 as rs
import numpy as np


def camera_matrix(intrinsics):
    return np.array([[intrinsics.fx, 0, intrinsics.ppx],
                     [0, intrinsics.fy, intrinsics.ppy],
                     [0, 0, 1]])


def fisheye_distortion(intrinsics):
    return np.array(intrinsics.coeffs[:4])


pipe = rs.pipeline()
cfg = rs.config()
pipe.start(cfg)

profiles = pipe.get_active_profile()
stream = profiles.get_stream(rs.stream.depth).as_video_stream_profile()
intrinsics = stream.get_intrinsics()

print(f"Depth Intrinsics: {intrinsics}")

print("Camera Matrix:")
print(camera_matrix(intrinsics))

print("Fisheye Distortion Matrix:")
print(fisheye_distortion(intrinsics))

pipe.stop()