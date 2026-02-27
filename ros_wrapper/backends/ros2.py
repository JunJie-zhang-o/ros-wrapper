from __future__ import annotations

import importlib
from typing import Any

from ros_wrapper.backends.base import ROSBackend
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

    def publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Any:
        qos = kwargs.pop("qos_profile", 10)
        return self.node.create_publisher(msg_type, topic, qos, **kwargs)

    def subscriber(
        self,
        topic: str,
        msg_type: Any,
        callback: Any,
        **kwargs: Any,
    ) -> Any:
        qos = kwargs.pop("qos_profile", 10)
        return self.node.create_subscription(msg_type, topic, callback, qos, **kwargs)

    def service_client(self, name: str, srv_type: Any, **kwargs: Any) -> Any:
        return self.node.create_client(srv_type, name, **kwargs)

    def service_server(
        self,
        name: str,
        srv_type: Any,
        handler: Any,
        **kwargs: Any,
    ) -> Any:
        return self.node.create_service(srv_type, name, handler, **kwargs)

    def action_client(self, name: str, action_type: Any, **kwargs: Any) -> Any:
        return self._action_mod.ActionClient(self.node, action_type, name, **kwargs)

    def action_server(
        self,
        name: str,
        action_type: Any,
        execute_callback: Any,
        **kwargs: Any,
    ) -> Any:
        return self._action_mod.ActionServer(
            self.node,
            action_type,
            name,
            execute_callback=execute_callback,
            **kwargs,
        )

    def spin(self) -> None:
        self._rclpy.spin(self.node)

    def shutdown(self) -> None:
        if self._node is not None:
            self._node.destroy_node()
            self._node = None
        if self._owns_context and self._rclpy.ok():
            self._rclpy.shutdown()
            self._owns_context = False
