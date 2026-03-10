from __future__ import annotations

import importlib
from typing import Any

from ros_wrapper.backends.base import ROSBackend
from ros_wrapper.clients import (
    ActionClient,
    ActionServer,
    Publisher,
    ServiceClient,
    ServiceServer,
    Subscriber,
    _wrap_action_execute_for_ros2,
    _wrap_service_handler_for_ros2,
)
from ros_wrapper.config import ROSConfig, ROSVersion
from ros_wrapper.exceptions import ROSRuntimeUnavailableError


class ROS2Backend(ROSBackend):
    version = ROSVersion.ROS2

    def __init__(self, config: ROSConfig) -> None:
        self._config = config
        self._rclpy = self._load_module("rclpy")
        self._action_mod = self._load_module("rclpy.action")
        self._owns_context = False
        self._node = None
        if config.auto_init:
            self.init()

    def _load_module(self, name: str) -> Any:
        try:
            return importlib.import_module(name)
        except ModuleNotFoundError as exc:
            raise ROSRuntimeUnavailableError(
                f"ROS2 runtime module {name!r} is unavailable. "
                "Please source ROS2 env and install rclpy."
            ) from exc

    @property
    def node(self) -> Any:
        if self._node is None:
            self._maybe_init_context()
            self._node = self._create_node()
        return self._node

    def _maybe_init_context(self) -> None:
        if not self._rclpy.ok():
            args = self._config.backend_kwargs.get("args")
            self._rclpy.init(args=args)
            self._owns_context = True

    def _create_node(self) -> Any:
        if self._config.namespace:
            return self._rclpy.create_node(
                self._config.node_name,
                namespace=self._config.namespace,
            )
        return self._rclpy.create_node(self._config.node_name)

    def init(self) -> None:
        self._maybe_init_context()
        if self._node is None:
            self._node = self._create_node()

    def publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Publisher:
        qos = kwargs.pop("qos_profile", 10)
        native = self.node.create_publisher(msg_type, topic, qos, **kwargs)
        return Publisher(native)

    def subscriber(
        self,
        topic: str,
        msg_type: Any,
        callback: Any,
        **kwargs: Any,
    ) -> Subscriber:
        qos = kwargs.pop("qos_profile", 10)
        native = self.node.create_subscription(msg_type, topic, callback, qos, **kwargs)
        return Subscriber(native)

    def service_client(self, name: str, srv_type: Any, **kwargs: Any) -> ServiceClient:
        native = self.node.create_client(srv_type, name, **kwargs)
        return ServiceClient(native, version="ros2", node=self.node)

    def service_server(
        self,
        name: str,
        srv_type: Any,
        handler: Any,
        **kwargs: Any,
    ) -> ServiceServer:
        ros2_handler = _wrap_service_handler_for_ros2(handler)
        native = self.node.create_service(srv_type, name, ros2_handler, **kwargs)
        return ServiceServer(native)

    def action_client(self, name: str, action_type: Any, **kwargs: Any) -> ActionClient:
        native = self._action_mod.ActionClient(self.node, action_type, name, **kwargs)
        return ActionClient(native, version="ros2", node=self.node)

    def action_server(
        self,
        name: str,
        action_type: Any,
        execute_callback: Any,
        **kwargs: Any,
    ) -> ActionServer:
        wrapped_cb = _wrap_action_execute_for_ros2(execute_callback)
        native = self._action_mod.ActionServer(
            self.node,
            action_type,
            name,
            execute_callback=wrapped_cb,
            **kwargs,
        )
        return ActionServer(native)

    def spin(self) -> None:
        self._rclpy.spin(self.node)

    def shutdown(self) -> None:
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
        if self._owns_context and self._rclpy.ok():
            self._rclpy.shutdown()
            self._owns_context = False
