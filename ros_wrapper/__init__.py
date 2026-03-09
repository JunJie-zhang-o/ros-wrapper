"""Unified ROS1/ROS2 wrapper APIs."""

from ros_wrapper.clients import (
    ActionClient,
    ActionGoalHandle,
    ActionServer,
    Publisher,
    ServerGoalHandle,
    ServiceClient,
    ServiceServer,
    Subscriber,
)
from ros_wrapper.config import ROSConfig, ROSVersion
from ros_wrapper.core import ROSWrapper, create_wrapper
from ros_wrapper.meta import ROSMeta, get_ros_meta

__all__ = [
    # Config / version
    "ROSConfig",
    "ROSVersion",
    # Wrapper facade
    "ROSWrapper",
    "create_wrapper",
    # Metadata
    "ROSMeta",
    "get_ros_meta",
    # Unified compatible client/server types
    "Publisher",
    "Subscriber",
    "ServiceClient",
    "ServiceServer",
    "ActionClient",
    "ActionGoalHandle",
    "ActionServer",
    "ServerGoalHandle",
]

__version__ = "0.1.0"
