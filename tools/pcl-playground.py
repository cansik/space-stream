import cv2
import open3d
import visiongraph as vg
import numpy as np
from typing import Tuple


def calculate_point_wise_distance(a: open3d.geometry.PointCloud, b: open3d.geometry.PointCloud) -> float:
    pts_a = np.asarray(a.points)
    pts_b = np.asarray(b.points)

    assert pts_a.shape == pts_b.shape == (pts_a.shape[0], 3)

    distances = np.linalg.norm(pts_a - pts_b, axis=1)
    return float(np.sum(distances))


def depthmap_to_pointcloud(depth_map: np.ndarray,
                           calibration: vg.CameraIntrinsics,
                           extrinsics: Tuple[np.ndarray, np.ndarray] = (np.eye(3), np.zeros(3)),
                           undistort: bool = False) -> np.ndarray:
    h, w = depth_map.shape[:2]
    fx, fy, cx, cy = calibration.fx, calibration.fy, calibration.px, calibration.py
    R, T = extrinsics

    if undistort:
        # apply inverse rectify (calculate out distortion)
        ix, iy = cv2.initInverseRectificationMap(calibration.intrinsic_matrix, calibration.distortion_coefficients,
                                                 None, calibration.intrinsic_matrix, (w, h), 5)

        u = ix.flatten()
        v = iy.flatten()
    else:
        u, v = np.meshgrid(range(depth_map.shape[1]), range(depth_map.shape[0]))
        u = u.flatten()
        v = v.flatten()

    Z = depth_map.flatten()

    # Convert to homogeneous coordinates
    points_camera = np.vstack([(u - cx) * Z / fx, (v - cy) * Z / fy, Z, np.ones_like(u)])

    # Transform to world coordinates
    points_world = np.dot(R, points_camera[:3, :]) + T.reshape(-1, 1)

    return points_world.T


def pcl_from_custom(azure: vg.AzureKinectInput) -> open3d.geometry.PointCloud:
    calib = azure.get_intrinsics(vg.CameraStreamType.Depth)

    # depth image
    depth = azure.depth
    h, w = depth.shape[:2]

    # inverse recitfied
    ix, iy = cv2.initInverseRectificationMap(calib.intrinsic_matrix, calib.distortion_coefficients,
                                             None, calib.intrinsic_matrix, (w, h), 5)
    dst_inverse_rect = cv2.remap(depth, ix, iy, cv2.INTER_LINEAR)

    # rectified
    ix, iy = cv2.initUndistortRectifyMap(calib.intrinsic_matrix, calib.distortion_coefficients,
                                         None, calib.intrinsic_matrix, (w, h), 5)
    dst_rect = cv2.remap(depth, ix, iy, cv2.INTER_NEAREST)

    preview = np.hstack((depth, dst_inverse_rect, dst_rect))

    # calib.distortion_coefficients
    points = depthmap_to_pointcloud(dst_rect, calib, undistort=False)

    # points = points[np.where(points[:, 2] > 0)]

    pcl: open3d.geometry.PointCloud = open3d.cpu.pybind.geometry.PointCloud()
    pcl.points = open3d.utility.Vector3dVector(points)

    colors = azure.transformed_color[..., (2, 1, 0)].reshape((-1, 3))
    pcl.colors = open3d.utility.Vector3dVector(colors / 255)

    return pcl


def pcl_from_azure(azure: vg.AzureKinectInput) -> open3d.geometry.PointCloud:
    points = azure.capture.depth_point_cloud.reshape((-1, 3))
    colors = azure.transformed_color[..., (2, 1, 0)].reshape((-1, 3))

    pcl: open3d.geometry.PointCloud = open3d.cpu.pybind.geometry.PointCloud()
    pcl.points = open3d.utility.Vector3dVector(points)
    pcl.colors = open3d.utility.Vector3dVector(colors / 255)

    return pcl


def pcl_from_open3d(azure: vg.AzureKinectInput) -> open3d.geometry.PointCloud:
    extrinsics = open3d.core.Tensor.eye(4, dtype=open3d.core.Dtype.Float32)
    cam = azure.get_intrinsics(vg.CameraStreamType.Depth)
    intrinsic_matrix = open3d.core.Tensor(cam.intrinsic_matrix, dtype=open3d.core.Dtype.Float32)

    depth_max = 5000  # mm
    pcd_stride = 1
    flag_normals = False
    depth_scale = 1

    depth_frame = open3d.t.geometry.Image(azure.capture.depth)

    pcd: open3d.t.geometry.PointCloud = open3d.t.geometry.PointCloud.create_from_depth_image(depth_frame,
                                                                                             intrinsic_matrix,
                                                                                             extrinsics,
                                                                                             depth_scale,
                                                                                             depth_max,
                                                                                             pcd_stride,
                                                                                             flag_normals)

    return pcd.to_legacy()


def main() -> int:
    print("startup camera...")
    azure = vg.AzureKinectInput()
    azure.input_mkv_file = "recordings/stairs.mkv"
    azure.setup()

    print("reading frame...")
    for i in range(5):
        azure.read()

    with vg.Watch("PCL from Azure"):
        azure_pcl = pcl_from_azure(azure)

    with vg.Watch("PCL from Open3d"):
        o3d_pcl = pcl_from_open3d(azure)

    with vg.Watch("PCL from Custom"):
        custom_pcl = pcl_from_custom(azure)

    # colorize pcls
    azure_pcl.paint_uniform_color([0, 1, 0])
    o3d_pcl.paint_uniform_color([0, 0, 1])
    custom_pcl.paint_uniform_color([1, 0, 0])
    # custom_pcl.translate(np.array([4000, 0, 0]))

    # distance = calculate_point_wise_distance(azure_pcl, custom_pcl)
    # print(f"PCL Distance: {distance:.4f}")

    open3d.visualization.draw_geometries([azure_pcl, custom_pcl], "Point Clouds")

    print("releasing camera...")
    azure.release()
    return 0


if __name__ == "__main__":
    exit(main())
