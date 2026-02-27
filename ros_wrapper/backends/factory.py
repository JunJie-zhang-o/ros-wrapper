from __future__ import annotations

from ros_wrapper.backends.base import ROSBackend
from ros_wrapper.backends.ros1 import ROS1Backend
from ros_wrapper.backends.ros2 import ROS2Backend
from ros_wrapper.config import ROSConfig, ROSVersion


def create_backend(config: ROSConfig) -> ROSBackend:
    version = config.normalized_version()
    if version is ROSVersion.ROS1:
        return ROS1Backend(config)
    return ROS2Backend(config)
