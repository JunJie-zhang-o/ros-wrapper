from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ros_wrapper.config import ROSVersion


class ROSBackend(ABC):
    """Interface for ROS runtime adapters."""

    version: ROSVersion

    @abstractmethod
    def publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def subscriber(
        self,
        topic: str,
        msg_type: Any,
        callback: Any,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def service_client(self, name: str, srv_type: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def service_server(
        self,
        name: str,
        srv_type: Any,
        handler: Any,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def action_client(self, name: str, action_type: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def action_server(
        self,
        name: str,
        action_type: Any,
        execute_callback: Any,
        **kwargs: Any,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def spin(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        raise NotImplementedError
