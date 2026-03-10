from __future__ import annotations

from typing import Any, Callable, Optional


class Publisher:
    _native: Any
    def __init__(self, native: Any) -> None: ...
    def publish(self, msg: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


class Subscriber:
    _native: Any
    def __init__(self, native: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


class ServiceClient:
    _native: Any
    _version: str
    _node: Any
    def __init__(self, native: Any, version: str, node: Any = ...) -> None: ...
    def wait_for_service(self, timeout: Optional[float] = ...) -> bool: ...
    def call_async(self, request: Any) -> Any: ...
    def call(self, request: Any, timeout: Optional[float] = ...) -> Any: ...
    def __call__(self, request: Any, timeout: Optional[float] = ...) -> Any: ...
    def __getattr__(self, name: str) -> Any: ...


class ServiceServer:
    _native: Any
    def __init__(self, native: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


def _wrap_service_handler_for_ros1(
    srv_type: Any,
    handler: Callable[..., Any],
) -> Callable[[Any], Any]: ...
def _wrap_service_handler_for_ros2(
    handler: Callable[..., Any],
) -> Callable[..., Any]: ...


class ActionGoalHandle:
    _version: str
    _ros1_client: Any
    _ros2_handle: Any
    _node: Any
    def __init__(
        self,
        version: str,
        ros1_client: Any = ...,
        ros2_goal_handle: Any = ...,
        node: Any = ...,
    ) -> None: ...
    def cancel(self) -> None: ...
    def get_result(self, timeout: Optional[float] = ...) -> Any: ...


class ActionClient:
    _native: Any
    _version: str
    _node: Any
    def __init__(self, native: Any, version: str, node: Any = ...) -> None: ...
    def wait_for_server(self, timeout: Optional[float] = ...) -> bool: ...
    def send_goal(
        self,
        goal: Any,
        feedback_callback: Optional[Callable[..., Any]] = ...,
    ) -> ActionGoalHandle: ...
    def send_goal_and_wait(
        self,
        goal: Any,
        timeout: Optional[float] = ...,
        feedback_callback: Optional[Callable[..., Any]] = ...,
    ) -> Any: ...
    def call(
        self,
        goal: Any,
        timeout: Optional[float] = ...,
        feedback_callback: Optional[Callable[..., Any]] = ...,
    ) -> Any: ...
    def call_async(
        self,
        goal: Any,
        feedback_callback: Optional[Callable[..., Any]] = ...,
    ) -> ActionGoalHandle: ...
    def send_goal_async(
        self,
        goal: Any,
        feedback_callback: Optional[Callable[..., Any]] = ...,
    ) -> ActionGoalHandle: ...
    def __getattr__(self, name: str) -> Any: ...


class ServerGoalHandle:
    _version: str
    _request: Any
    _ros1_server: Any
    _ros2_handle: Any
    def __init__(
        self,
        version: str,
        request: Any,
        ros1_server: Any = ...,
        ros2_goal_handle: Any = ...,
    ) -> None: ...
    @property
    def request(self) -> Any: ...
    @property
    def is_cancel_requested(self) -> bool: ...
    def publish_feedback(self, feedback: Any) -> None: ...
    def succeed(self) -> None: ...
    def abort(self) -> None: ...
    def canceled(self) -> None: ...


class ActionServer:
    _native: Any
    def __init__(self, native: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


def _wrap_action_execute_for_ros1(
    server_ref: list[Any],
    handler: Callable[..., Any],
) -> Callable[[Any], None]: ...
def _wrap_action_execute_for_ros2(
    handler: Callable[..., Any],
) -> Callable[[Any], Any]: ...
