from __future__ import annotations

import importlib
from typing import Any

from ros_wrapper.backends.base import ROSBackend
from ros_wrapper.config import ROSConfig, ROSVersion
from ros_wrapper.exceptions import ROSRuntimeUnavailableError


class ROS1Backend(ROSBackend):
    version = ROSVersion.ROS1

    def __init__(self, config: ROSConfig) -> None:
        self._config = config
        self._rospy = self._load_module("rospy")
        if config.auto_init:
            self.init()

    def _load_module(self, name: str) -> Any:
        try:
            return importlib.import_module(name)
        except ModuleNotFoundError as exc:
            raise ROSRuntimeUnavailableError(
                f"ROS1 runtime module {name!r} is unavailable. "
                "Please source ROS1 env and install rospy/actionlib."
            ) from exc

    def _maybe_init_node(self) -> None:
        rospy = self._rospy
        initialized = False
        try:
            initialized = bool(rospy.core.is_initialized())
        except Exception:
            initialized = False
        if not initialized:
            rospy.init_node(self._config.node_name, disable_signals=True)

    def init(self) -> None:
        self._maybe_init_node()

    def publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("queue_size", 10)
        return self._rospy.Publisher(topic, msg_type, **kwargs)

    def subscriber(
        self,
        topic: str,
        msg_type: Any,
        callback: Any,
        **kwargs: Any,
    ) -> Any:
        kwargs.setdefault("queue_size", 10)
        return self._rospy.Subscriber(topic, msg_type, callback, **kwargs)

    def service_client(self, name: str, srv_type: Any, **kwargs: Any) -> Any:
        return self._rospy.ServiceProxy(name, srv_type, **kwargs)

    def service_server(
        self,
        name: str,
        srv_type: Any,
        handler: Any,
        **kwargs: Any,
    ) -> Any:
        return self._rospy.Service(name, srv_type, handler, **kwargs)

    def action_client(self, name: str, action_type: Any, **kwargs: Any) -> Any:
        actionlib = self._load_module("actionlib")
        return actionlib.SimpleActionClient(name, action_type, **kwargs)

    def action_server(
        self,
        name: str,
        action_type: Any,
        execute_callback: Any,
        **kwargs: Any,
    ) -> Any:
        actionlib = self._load_module("actionlib")
        kwargs.setdefault("auto_start", True)
        return actionlib.SimpleActionServer(
            name,
            action_type,
            execute_cb=execute_callback,
            **kwargs,
        )

    def spin(self) -> None:
        self._rospy.spin()

    def shutdown(self) -> None:
        try:
            self._rospy.signal_shutdown("ros_wrapper shutdown")
        except Exception:
            return
