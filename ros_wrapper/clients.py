"""Unified compatible client/server wrappers for ROS1 and ROS2.

These wrappers provide a single, consistent API regardless of the underlying
ROS version, so user code never needs to branch on ROS1 vs ROS2.

Unified API summary
-------------------
Publisher
    publish(msg)

Subscriber
    (no public methods; callbacks are registered at creation time)

ServiceClient
    call(request, timeout=None) -> response   # always synchronous
    call_async(request) -> Future/ROS2Future
    wait_for_service(timeout=None) -> bool

ServiceServer
    handler signature:  handler(request, response) -> response
    (ROS1 handler is wrapped automatically)

ActionClient
    wait_for_server(timeout=None) -> bool
    send_goal(goal, feedback_callback=None) -> GoalHandle
    send_goal_and_wait(goal, timeout=None) -> result
    call(goal, timeout=None, feedback_callback=None) -> result
    call_async(goal, feedback_callback=None) -> GoalHandle
    cancel_goal(goal_handle)

ActionServer
    execute_callback signature:  execute_callback(goal_handle) -> result
    GoalHandle interface (passed to execute_callback):
        goal_handle.request          # the goal message
        goal_handle.publish_feedback(feedback)
        goal_handle.succeed()
        goal_handle.abort()
        goal_handle.canceled()
        goal_handle.is_cancel_requested  # bool property
"""
from __future__ import annotations

from concurrent.futures import Future
from threading import Thread
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------

class Publisher:
    """Thin wrapper — publish() is identical on both versions."""

    def __init__(self, native: Any) -> None:
        self._native = native

    def publish(self, msg: Any) -> None:
        self._native.publish(msg)

    # Forward any attribute not defined here to the native object so that
    # version-specific extras remain accessible if needed.
    def __getattr__(self, name: str) -> Any:
        return getattr(self._native, name)


# ---------------------------------------------------------------------------
# Subscriber
# ---------------------------------------------------------------------------

class Subscriber:
    """Thin wrapper around a native subscriber (no extra API needed)."""

    def __init__(self, native: Any) -> None:
        self._native = native

    def __getattr__(self, name: str) -> Any:
        return getattr(self._native, name)


# ---------------------------------------------------------------------------
# ServiceClient
# ---------------------------------------------------------------------------

class ServiceClient:
    """Service client compatible with both ROS1 and ROS2.

    Usage::

        client = wrapper.service_client("/add", AddTwoInts)
        # Works on ROS1 and ROS2:
        response = client.call(request)
        response = client.call(request, timeout=5.0)
        future = client.call_async(request)
        response = future.result()
    """

    def __init__(self, native: Any, version: str, node: Any = None) -> None:
        """
        Parameters
        ----------
        native:
            The native ROS client object (rospy.ServiceProxy or
            rclpy client).
        version:
            ``"ros1"`` or ``"ros2"``.
        node:
            The rclpy node, required for ROS2 to spin the future.
        """
        self._native = native
        self._version = version
        self._node = node  # only used for ROS2

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def wait_for_service(self, timeout: Optional[float] = None) -> bool:
        """Block until the service is available.

        Returns True if became available, False on timeout.
        """
        if self._version == "ros1":
            try:
                import rospy
                rospy.wait_for_service(
                    self._native.resolved_name,
                    timeout=timeout,
                )
                return True
            except Exception:
                return False
        else:
            kwargs = {}
            if timeout is not None:
                kwargs["timeout_sec"] = float(timeout)
            else:
                kwargs["timeout_sec"] = 1.0
            # Poll until available or timeout
            import time
            deadline = None if timeout is None else time.monotonic() + timeout
            while True:
                if self._native.wait_for_service(**kwargs):
                    return True
                if deadline is not None and time.monotonic() >= deadline:
                    return False

    def call_async(self, request: Any) -> Any:
        """Invoke service asynchronously for both ROS versions.

        ROS2 delegates directly to ``native.call_async``.
        ROS1 runs the blocking service call in a background thread and
        returns ``concurrent.futures.Future``.
        """
        if self._version == "ros2":
            return self._native.call_async(request)

        future: Future = Future()

        def _invoke() -> None:
            try:
                future.set_result(self._native(request))
            except Exception as exc:
                future.set_exception(exc)

        Thread(target=_invoke, daemon=True).start()
        return future

    def _wait_ros2_future(self, future: Any, timeout: Optional[float]) -> None:
        if self._node is not None:
            import rclpy
            rclpy.spin_until_future_complete(
                self._node,
                future,
                timeout_sec=timeout,
            )
        else:
            # Fallback when node is unavailable in tests/mocks.
            import time
            deadline = None if timeout is None else time.monotonic() + timeout
            while not future.done():
                time.sleep(0.01)
                if deadline is not None and time.monotonic() >= deadline:
                    break

        if timeout is not None and not future.done():
            raise TimeoutError("Service call timed out")

    def call(self, request: Any, timeout: Optional[float] = None) -> Any:
        """Call the service synchronously and return the response."""
        future = self.call_async(request)
        if self._version == "ros2":
            self._wait_ros2_future(future, timeout)
            return future.result()
        return future.result(timeout=timeout)

    # Allow direct call syntax:  client(request)
    def __call__(self, request: Any, timeout: Optional[float] = None) -> Any:
        return self.call(request, timeout=timeout)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._native, name)


# ---------------------------------------------------------------------------
# ServiceServer
# ---------------------------------------------------------------------------

class ServiceServer:
    """Service server wrapper that normalises the handler signature.

    Both ROS versions will use:  ``handler(request, response) -> response``

    For ROS1 the handler is adapted automatically (ROS1 expects
    ``handler(request) -> response_value``).
    """

    def __init__(self, native: Any) -> None:
        self._native = native

    def __getattr__(self, name: str) -> Any:
        return getattr(self._native, name)


def _wrap_service_handler_for_ros1(srv_type: Any, handler: Callable) -> Callable:
    """Return a ROS1-compatible handler that calls the unified handler.

    Unified handler signature: ``handler(request, response) -> response``
    ROS1 handler signature:    ``handler(request) -> response``
    """
    def ros1_handler(request: Any) -> Any:
        response = srv_type._response_class()
        return handler(request, response)
    return ros1_handler


def _wrap_service_handler_for_ros2(handler: Callable) -> Callable:
    """Return a ROS2-compatible handler.

    Unified handler: ``handler(request, response) -> response``
    ROS2 handler:    ``handler(request, response) -> response``  — already identical.
    """
    return handler


# ---------------------------------------------------------------------------
# ActionClient
# ---------------------------------------------------------------------------

class ActionGoalHandle:
    """Client-side goal handle returned by ActionClient.send_goal().

    Provides a unified interface over ROS1 SimpleActionClient (which keeps
    all state on the client) and the ROS2 goal handle object.
    """

    def __init__(
        self,
        version: str,
        ros1_client: Any = None,
        ros2_goal_handle: Any = None,
        node: Any = None,
    ) -> None:
        self._version = version
        self._ros1_client = ros1_client      # SimpleActionClient instance
        self._ros2_handle = ros2_goal_handle  # rclpy GoalHandle
        self._node = node

    def cancel(self) -> None:
        """Cancel this goal."""
        if self._version == "ros1":
            self._ros1_client.cancel_goal()
        else:
            future = self._ros2_handle.cancel_goal_async()
            if self._node is not None:
                import rclpy
                rclpy.spin_until_future_complete(self._node, future)

    @staticmethod
    def _wait_future_done(future: Any, timeout: Optional[float]) -> None:
        import time

        deadline = None if timeout is None else time.monotonic() + timeout
        while hasattr(future, "done") and not future.done():
            time.sleep(0.01)
            if deadline is not None and time.monotonic() >= deadline:
                break
        if timeout is not None and hasattr(future, "done") and not future.done():
            raise TimeoutError("Action result timed out")

    def get_result(self, timeout: Optional[float] = None) -> Any:
        """Block and return the action result."""
        if self._version == "ros1":
            self._ros1_client.wait_for_result(
                timeout=None if timeout is None else
                self._ros1_client._rospy.Duration(timeout)
            )
            return self._ros1_client.get_result()
        else:
            future = self._ros2_handle.get_result_async()
            if self._node is not None:
                import rclpy
                rclpy.spin_until_future_complete(
                    self._node, future, timeout_sec=timeout
                )
                if timeout is not None and hasattr(future, "done") and not future.done():
                    raise TimeoutError("Action result timed out")
            else:
                self._wait_future_done(future, timeout)
            return future.result().result


class ActionClient:
    """Unified action client compatible with ROS1 and ROS2.

    Usage::

        client = wrapper.action_client("/fibonacci", Fibonacci)
        client.wait_for_server()
        goal = Fibonacci.Goal()
        goal.order = 8
        result = client.send_goal_and_wait(goal)

        # Or asynchronously:
        handle = client.send_goal(goal, feedback_callback=on_feedback)
        result = handle.get_result()
    """

    def __init__(self, native: Any, version: str, node: Any = None) -> None:
        self._native = native
        self._version = version
        self._node = node

    def wait_for_server(self, timeout: Optional[float] = None) -> bool:
        """Block until the action server is available."""
        if self._version == "ros1":
            import rospy
            return self._native.wait_for_server(
                timeout=rospy.Duration(timeout) if timeout is not None
                else rospy.Duration()
            )
        else:
            kwargs = {}
            if timeout is not None:
                kwargs["timeout_sec"] = float(timeout)
            return self._native.wait_for_server(**kwargs)

    def send_goal(
        self,
        goal: Any,
        feedback_callback: Optional[Callable] = None,
    ) -> ActionGoalHandle:
        """Send a goal and return an ActionGoalHandle immediately."""
        if self._version == "ros1":
            def _ros1_feedback_cb(feedback: Any) -> None:
                if feedback_callback is not None:
                    feedback_callback(feedback)

            self._native.send_goal(
                goal,
                feedback_cb=_ros1_feedback_cb if feedback_callback else None,
            )
            return ActionGoalHandle(
                version="ros1",
                ros1_client=self._native,
                node=self._node,
            )
        else:
            future = self._native.send_goal_async(
                goal,
                feedback_callback=feedback_callback,
            )
            if self._node is not None:
                import rclpy
                rclpy.spin_until_future_complete(self._node, future)
            else:
                ActionGoalHandle._wait_future_done(future, timeout=None)
            goal_handle = future.result()
            return ActionGoalHandle(
                version="ros2",
                ros2_goal_handle=goal_handle,
                node=self._node,
            )

    def send_goal_and_wait(
        self,
        goal: Any,
        timeout: Optional[float] = None,
        feedback_callback: Optional[Callable] = None,
    ) -> Any:
        """Send a goal, block until done, and return the result directly."""
        handle = self.send_goal(goal, feedback_callback=feedback_callback)
        return handle.get_result(timeout=timeout)

    # Unified naming aliases, aligned with ServiceClient
    # - call(): synchronous (result)
    # - call_async(): asynchronous (goal handle)
    call = send_goal_and_wait
    call_async = send_goal
    # ROS2-friendly alias; both backends use the same send path.
    send_goal_async = send_goal

    def __getattr__(self, name: str) -> Any:
        return getattr(self._native, name)


# ---------------------------------------------------------------------------
# ActionServer — unified GoalHandle passed to execute_callback
# ---------------------------------------------------------------------------

class ServerGoalHandle:
    """Unified server-side goal handle.

    Wraps ROS1's SimpleActionServer (which exposes state via the server
    object itself) and ROS2's native GoalHandle.

    Execute-callback signature::

        def execute(goal_handle: ServerGoalHandle) -> result
            goal_handle.request           # the goal message
            goal_handle.publish_feedback(feedback_msg)
            goal_handle.is_cancel_requested  # bool
            goal_handle.succeed()
            goal_handle.abort()
            goal_handle.canceled()
    """

    def __init__(
        self,
        version: str,
        request: Any,
        ros1_server: Any = None,
        ros2_goal_handle: Any = None,
    ) -> None:
        self._version = version
        self._request = request
        self._ros1_server = ros1_server
        self._ros2_handle = ros2_goal_handle

    @property
    def request(self) -> Any:
        return self._request

    @property
    def is_cancel_requested(self) -> bool:
        if self._version == "ros1":
            return bool(self._ros1_server.is_preempt_requested())
        else:
            return bool(self._ros2_handle.is_cancel_requested)

    def publish_feedback(self, feedback: Any) -> None:
        if self._version == "ros1":
            self._ros1_server.publish_feedback(feedback)
        else:
            self._ros2_handle.publish_feedback(feedback)

    def succeed(self) -> None:
        """Mark goal as succeeded (ROS2 only; ROS1 handled in set_succeeded)."""
        if self._version == "ros2":
            self._ros2_handle.succeed()

    def abort(self) -> None:
        if self._version == "ros2":
            self._ros2_handle.abort()

    def canceled(self) -> None:
        if self._version == "ros2":
            self._ros2_handle.canceled()


class ActionServer:
    """Unified action server wrapper.

    The execute_callback receives a ``ServerGoalHandle`` instead of the
    version-specific types, and must return a result object.

    ROS1 wrapping
    ~~~~~~~~~~~~~
    ROS1's ``SimpleActionServer`` calls ``execute_cb(goal_msg)`` and the
    server state (publish_feedback, set_succeeded, …) lives on the server
    object itself.  We adapt this to the unified ``execute_cb(goal_handle)``.

    ROS2 wrapping
    ~~~~~~~~~~~~~
    ROS2's ``ActionServer`` calls ``execute_cb(goal_handle)`` where the goal
    handle already carries most of the API, except we add ``request`` as a
    convenience alias for ``goal_handle.request``.
    """

    def __init__(self, native: Any) -> None:
        self._native = native

    def __getattr__(self, name: str) -> Any:
        return getattr(self._native, name)


def _wrap_action_execute_for_ros1(server_ref: list, handler: Callable) -> Callable:
    """Adapt the unified execute handler for ROS1 SimpleActionServer.

    ``server_ref`` is a one-element list that will be filled with the
    SimpleActionServer after construction (late-binding).
    """
    def ros1_execute(goal_msg: Any) -> None:
        native_server = server_ref[0]
        goal_handle = ServerGoalHandle(
            version="ros1",
            request=goal_msg,
            ros1_server=native_server,
        )
        result = handler(goal_handle)
        if goal_handle.is_cancel_requested:
            native_server.set_preempted()
        else:
            native_server.set_succeeded(result)
    return ros1_execute


def _wrap_action_execute_for_ros2(handler: Callable) -> Callable:
    """Adapt the unified execute handler for ROS2 ActionServer."""
    def ros2_execute(ros2_goal_handle: Any) -> Any:
        goal_handle = ServerGoalHandle(
            version="ros2",
            request=ros2_goal_handle.request,
            ros2_goal_handle=ros2_goal_handle,
        )
        return handler(goal_handle)
    return ros2_execute
