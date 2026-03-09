"""Tests for ros_wrapper.clients — unified compatible wrappers.

All tests run without a real ROS runtime by using lightweight mock objects
that mimic the native ROS1/ROS2 client interfaces.
"""
from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock, patch

from ros_wrapper.clients import (
    ActionClient,
    ActionGoalHandle,
    ActionServer,
    Publisher,
    ServerGoalHandle,
    ServiceClient,
    ServiceServer,
    Subscriber,
    _wrap_action_execute_for_ros1,
    _wrap_action_execute_for_ros2,
    _wrap_service_handler_for_ros1,
    _wrap_service_handler_for_ros2,
)


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------

class FakeMsg:
    data: str = "hello"


class FakeSrv:
    class Request:
        a: int = 1
        b: int = 2

    class Response:
        sum: int = 0

    _response_class = Response


class FakeGoal:
    order: int = 5


class FakeFeedback:
    partial_sequence: list = []


class FakeResult:
    sequence: list = []


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------

class TestPublisher:
    def test_publish_delegates_to_native(self) -> None:
        native = MagicMock()
        pub = Publisher(native)
        msg = FakeMsg()
        pub.publish(msg)
        native.publish.assert_called_once_with(msg)

    def test_getattr_falls_through_to_native(self) -> None:
        native = MagicMock()
        native.topic = "/chatter"
        pub = Publisher(native)
        assert pub.topic == "/chatter"


# ---------------------------------------------------------------------------
# Subscriber
# ---------------------------------------------------------------------------

class TestSubscriber:
    def test_getattr_falls_through_to_native(self) -> None:
        native = MagicMock()
        native.topic = "/chatter"
        sub = Subscriber(native)
        assert sub.topic == "/chatter"


# ---------------------------------------------------------------------------
# ServiceClient — ROS1
# ---------------------------------------------------------------------------

class TestServiceClientROS1:
    def _make_client(self) -> tuple[ServiceClient, MagicMock]:
        native = MagicMock()
        native.resolved_name = "/add"
        client = ServiceClient(native, version="ros1")
        return client, native

    def test_call_invokes_native_directly(self) -> None:
        client, native = self._make_client()
        req = FakeSrv.Request()
        expected = FakeSrv.Response()
        expected.sum = 3
        native.return_value = expected
        resp = client.call(req)
        native.assert_called_once_with(req)
        assert resp is expected

    def test_call_async_returns_future(self) -> None:
        client, native = self._make_client()
        req = FakeSrv.Request()
        expected = FakeSrv.Response()
        native.return_value = expected
        future = client.call_async(req)
        assert future.result(timeout=1.0) is expected
        native.assert_called_once_with(req)

    def test_dunder_call_alias(self) -> None:
        client, native = self._make_client()
        req = FakeSrv.Request()
        client(req)
        native.assert_called_with(req)

    def test_wait_for_service_ros1(self) -> None:
        client, _native = self._make_client()
        rospy = MagicMock()
        rospy.wait_for_service.return_value = None
        with patch.dict(sys.modules, {"rospy": rospy}):
            result = client.wait_for_service(timeout=5.0)
        assert result is True

    def test_wait_for_service_ros1_timeout(self) -> None:
        client, _native = self._make_client()
        rospy = MagicMock()
        rospy.wait_for_service.side_effect = Exception("timeout")
        with patch.dict(sys.modules, {"rospy": rospy}):
            result = client.wait_for_service(timeout=1.0)
        assert result is False


# ---------------------------------------------------------------------------
# ServiceClient — ROS2
# ---------------------------------------------------------------------------

class TestServiceClientROS2:
    def _make_client(self) -> tuple[ServiceClient, MagicMock]:
        native = MagicMock()
        future = MagicMock()
        future.done.return_value = True
        future.result.return_value = FakeSrv.Response()
        native.call_async.return_value = future
        client = ServiceClient(native, version="ros2", node=None)
        return client, native

    def test_call_uses_call_async(self) -> None:
        client, native = self._make_client()
        req = FakeSrv.Request()
        resp = client.call(req)
        native.call_async.assert_called_once_with(req)
        assert isinstance(resp, FakeSrv.Response)

    def test_dunder_call_alias(self) -> None:
        client, native = self._make_client()
        req = FakeSrv.Request()
        client(req)
        native.call_async.assert_called_once_with(req)

    def test_call_async_delegates_to_native(self) -> None:
        client, native = self._make_client()
        req = FakeSrv.Request()
        future = client.call_async(req)
        assert future is native.call_async.return_value
        native.call_async.assert_called_once_with(req)


# ---------------------------------------------------------------------------
# Service handler wrappers
# ---------------------------------------------------------------------------

class TestServiceHandlerWrapping:
    def test_ros1_handler_wrapping(self) -> None:
        """Unified handler (req, resp) should be called correctly via ROS1 adapter."""
        received: list = []

        def unified_handler(req: Any, resp: Any) -> Any:
            received.append((req, resp))
            resp.sum = req.a + req.b
            return resp

        ros1_handler = _wrap_service_handler_for_ros1(FakeSrv, unified_handler)
        req = FakeSrv.Request()
        req.a, req.b = 3, 4
        result = ros1_handler(req)
        assert len(received) == 1
        assert result.sum == 7

    def test_ros2_handler_wrapping_is_passthrough(self) -> None:
        sentinel: list = []

        def handler(req: Any, resp: Any) -> Any:
            sentinel.append(True)
            return resp

        ros2_handler = _wrap_service_handler_for_ros2(handler)
        assert ros2_handler is handler


# ---------------------------------------------------------------------------
# ActionClient — ROS1
# ---------------------------------------------------------------------------

class TestActionClientROS1:
    def _make_client(self) -> tuple[ActionClient, MagicMock]:
        native = MagicMock()
        client = ActionClient(native, version="ros1")
        return client, native

    def test_wait_for_server_delegates(self) -> None:
        client, native = self._make_client()
        native.wait_for_server.return_value = True
        rospy = MagicMock()
        rospy.Duration.side_effect = lambda t=None: t
        with patch.dict(sys.modules, {"rospy": rospy}):
            result = client.wait_for_server(timeout=5.0)
        assert result is True

    def test_send_goal_returns_goal_handle(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        handle = client.send_goal(goal)
        native.send_goal.assert_called_once()
        assert isinstance(handle, ActionGoalHandle)
        assert handle._version == "ros1"

    def test_send_goal_and_wait(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        expected_result = FakeResult()
        native.get_result.return_value = expected_result
        native.wait_for_result.return_value = None
        result = client.send_goal_and_wait(goal)
        assert result is expected_result

    def test_call_async_alias(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        handle = client.call_async(goal)
        native.send_goal.assert_called_once()
        assert isinstance(handle, ActionGoalHandle)

    def test_call_alias(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        expected_result = FakeResult()
        native.get_result.return_value = expected_result
        native.wait_for_result.return_value = None
        result = client.call(goal)
        assert result is expected_result


# ---------------------------------------------------------------------------
# ActionClient — ROS2
# ---------------------------------------------------------------------------

class TestActionClientROS2:
    def _make_client(self) -> tuple[ActionClient, MagicMock]:
        native = MagicMock()
        send_future = MagicMock()
        send_future.done.return_value = True
        ros2_goal_handle = MagicMock()
        send_future.result.return_value = ros2_goal_handle
        native.send_goal_async.return_value = send_future
        client = ActionClient(native, version="ros2", node=None)
        return client, native

    def test_send_goal_returns_goal_handle(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        handle = client.send_goal(goal)
        native.send_goal_async.assert_called_once()
        assert isinstance(handle, ActionGoalHandle)
        assert handle._version == "ros2"

    def test_send_goal_and_wait(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        result_future = MagicMock()
        result_future.done.return_value = True
        expected = FakeResult()
        result_future.result.return_value.result = expected
        native.send_goal_async.return_value.result.return_value.get_result_async.return_value = result_future
        result = client.send_goal_and_wait(goal)
        assert result is expected

    def test_call_async_alias(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        handle = client.call_async(goal)
        native.send_goal_async.assert_called_once()
        assert isinstance(handle, ActionGoalHandle)

    def test_call_alias(self) -> None:
        client, native = self._make_client()
        goal = FakeGoal()
        result_future = MagicMock()
        result_future.done.return_value = True
        expected = FakeResult()
        result_future.result.return_value.result = expected
        native.send_goal_async.return_value.result.return_value.get_result_async.return_value = result_future
        result = client.call(goal)
        assert result is expected


# ---------------------------------------------------------------------------
# ServerGoalHandle
# ---------------------------------------------------------------------------

class TestServerGoalHandle:
    def test_ros1_request_property(self) -> None:
        goal = FakeGoal()
        server = MagicMock()
        gh = ServerGoalHandle(version="ros1", request=goal, ros1_server=server)
        assert gh.request is goal

    def test_ros2_request_property(self) -> None:
        goal = FakeGoal()
        ros2_gh = MagicMock()
        gh = ServerGoalHandle(version="ros2", request=goal, ros2_goal_handle=ros2_gh)
        assert gh.request is goal

    def test_ros1_is_cancel_requested(self) -> None:
        server = MagicMock()
        server.is_preempt_requested.return_value = True
        gh = ServerGoalHandle(version="ros1", request=None, ros1_server=server)
        assert gh.is_cancel_requested is True

    def test_ros2_is_cancel_requested(self) -> None:
        ros2_gh = MagicMock()
        ros2_gh.is_cancel_requested = False
        gh = ServerGoalHandle(version="ros2", request=None, ros2_goal_handle=ros2_gh)
        assert gh.is_cancel_requested is False

    def test_ros1_publish_feedback(self) -> None:
        server = MagicMock()
        gh = ServerGoalHandle(version="ros1", request=None, ros1_server=server)
        fb = FakeFeedback()
        gh.publish_feedback(fb)
        server.publish_feedback.assert_called_once_with(fb)

    def test_ros2_publish_feedback(self) -> None:
        ros2_gh = MagicMock()
        gh = ServerGoalHandle(version="ros2", request=None, ros2_goal_handle=ros2_gh)
        fb = FakeFeedback()
        gh.publish_feedback(fb)
        ros2_gh.publish_feedback.assert_called_once_with(fb)

    def test_ros2_succeed(self) -> None:
        ros2_gh = MagicMock()
        gh = ServerGoalHandle(version="ros2", request=None, ros2_goal_handle=ros2_gh)
        gh.succeed()
        ros2_gh.succeed.assert_called_once()

    def test_ros2_abort(self) -> None:
        ros2_gh = MagicMock()
        gh = ServerGoalHandle(version="ros2", request=None, ros2_goal_handle=ros2_gh)
        gh.abort()
        ros2_gh.abort.assert_called_once()

    def test_ros2_canceled(self) -> None:
        ros2_gh = MagicMock()
        gh = ServerGoalHandle(version="ros2", request=None, ros2_goal_handle=ros2_gh)
        gh.canceled()
        ros2_gh.canceled.assert_called_once()


# ---------------------------------------------------------------------------
# Action execute callback wrappers
# ---------------------------------------------------------------------------

class TestActionExecuteWrapping:
    def test_ros1_execute_wrapper_calls_unified_handler(self) -> None:
        received_handles: list[ServerGoalHandle] = []
        result_obj = FakeResult()

        def unified_handler(gh: ServerGoalHandle) -> Any:
            received_handles.append(gh)
            return result_obj

        server = MagicMock()
        server.is_preempt_requested.return_value = False
        server_ref: list = [server]
        ros1_cb = _wrap_action_execute_for_ros1(server_ref, unified_handler)

        goal_msg = FakeGoal()
        ros1_cb(goal_msg)

        assert len(received_handles) == 1
        assert received_handles[0].request is goal_msg
        server.set_succeeded.assert_called_once_with(result_obj)

    def test_ros1_execute_wrapper_handles_preempt(self) -> None:
        result_obj = FakeResult()

        def unified_handler(gh: ServerGoalHandle) -> Any:
            return result_obj

        server = MagicMock()
        server.is_preempt_requested.return_value = True
        server_ref: list = [server]
        ros1_cb = _wrap_action_execute_for_ros1(server_ref, unified_handler)
        ros1_cb(FakeGoal())

        server.set_preempted.assert_called_once()
        server.set_succeeded.assert_not_called()

    def test_ros2_execute_wrapper_calls_unified_handler(self) -> None:
        received_handles: list[ServerGoalHandle] = []
        result_obj = FakeResult()

        def unified_handler(gh: ServerGoalHandle) -> Any:
            received_handles.append(gh)
            return result_obj

        ros2_cb = _wrap_action_execute_for_ros2(unified_handler)

        ros2_goal_handle = MagicMock()
        ros2_goal_handle.request = FakeGoal()
        ret = ros2_cb(ros2_goal_handle)

        assert ret is result_obj
        assert len(received_handles) == 1
        assert isinstance(received_handles[0], ServerGoalHandle)
        assert received_handles[0].request is ros2_goal_handle.request
