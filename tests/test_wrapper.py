from __future__ import annotations

from typing import Any

from ros_wrapper import (
    ROSConfig,
    ROSVersion,
    ROSWrapper,
    get_ros_meta,
    Publisher,
    Subscriber,
    ServiceClient,
    ServiceServer,
    ActionClient,
    ActionGoalHandle,
    ActionServer,
    ServerGoalHandle,
)
from ros_wrapper.backends.base import ROSBackend
from ros_wrapper.clients import (
    _wrap_action_execute_for_ros1,
    _wrap_action_execute_for_ros2,
    _wrap_service_handler_for_ros1,
    _wrap_service_handler_for_ros2,
)
from ros_wrapper.exceptions import ROSDecoratorUsageError


# ---------------------------------------------------------------------------
# Fake backend — returns unified wrapper types (as the real backends do)
# ---------------------------------------------------------------------------

class FakeNative:
    """Stand-in for a native ROS publisher / client / server object."""

    def __init__(self, kind: str, name: str) -> None:
        self.kind = kind
        self.name = name

    def publish(self, msg: Any) -> None:
        pass


class FakeBackend(ROSBackend):
    version = ROSVersion.ROS2

    def __init__(self) -> None:
        self.init_calls = 0
        self.spin_calls = 0
        self.shutdown_calls = 0

    def publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Publisher:
        return Publisher(FakeNative("publisher", topic))

    def subscriber(
        self,
        topic: str,
        msg_type: Any,
        callback: Any,
        **kwargs: Any,
    ) -> Subscriber:
        return Subscriber(FakeNative("subscriber", topic))

    def service_client(self, name: str, srv_type: Any, **kwargs: Any) -> ServiceClient:
        return ServiceClient(FakeNative("service_client", name), version="ros2", node=None)

    def service_server(
        self,
        name: str,
        srv_type: Any,
        handler: Any,
        **kwargs: Any,
    ) -> ServiceServer:
        return ServiceServer(FakeNative("service_server", name))

    def action_client(self, name: str, action_type: Any, **kwargs: Any) -> ActionClient:
        return ActionClient(FakeNative("action_client", name), version="ros2", node=None)

    def action_server(
        self,
        name: str,
        action_type: Any,
        execute_callback: Any,
        **kwargs: Any,
    ) -> ActionServer:
        return ActionServer(FakeNative("action_server", name))

    def init(self) -> None:
        self.init_calls += 1

    def spin(self) -> None:
        self.spin_calls += 1

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class Msg:
    pass


class Srv:
    _response_class = object

    class Response:
        pass


class Action:
    pass


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

def test_ros2_config_forces_auto_init_true() -> None:
    cfg = ROSConfig(version=ROSVersion.ROS2, auto_init=False)
    assert cfg.auto_init is True


def test_ros1_config_respects_auto_init_flag() -> None:
    cfg = ROSConfig(version=ROSVersion.ROS1, auto_init=False)
    assert cfg.auto_init is False


# ---------------------------------------------------------------------------
# Unified wrapper type tests — backends must return wrapper objects
# ---------------------------------------------------------------------------

def test_custom_api_returns_unified_wrapper_types() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS1, auto_init=False), backend=FakeBackend())

    assert isinstance(wrapper.publisher("/topic", Msg), Publisher)
    assert isinstance(wrapper.subscriber("/topic", Msg, callback=lambda _: None), Subscriber)
    assert isinstance(wrapper.service_client("/svc", Srv), ServiceClient)
    assert isinstance(wrapper.service_server("/svc", Srv), ServiceServer)
    assert isinstance(wrapper.action_client("/action", Action), ActionClient)
    assert isinstance(wrapper.action_server("/action", Action), ActionServer)


def test_ros1_compat_api_returns_unified_wrapper_types() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS1, auto_init=False), backend=FakeBackend())

    assert isinstance(wrapper.Publisher("/topic", Msg), Publisher)
    assert isinstance(wrapper.Subscriber("/topic", Msg, callback=lambda _: None), Subscriber)
    assert isinstance(wrapper.ServiceProxy("/svc", Srv), ServiceClient)
    assert isinstance(wrapper.Service("/svc", Srv, lambda _req, resp: resp), ServiceServer)
    assert isinstance(wrapper.SimpleActionClient("/action", Action), ActionClient)
    assert isinstance(wrapper.SimpleActionServer("/action", Action, execute_cb=lambda *_: None), ActionServer)


def test_ros2_compat_api_returns_unified_wrapper_types() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    assert isinstance(wrapper.create_publisher(Msg, "/topic", qos_profile=5), Publisher)
    assert isinstance(wrapper.create_subscription(Msg, "/topic", callback=lambda _: None, qos_profile=7), Subscriber)
    assert isinstance(wrapper.create_client(Srv, "/svc"), ServiceClient)
    assert isinstance(wrapper.create_service(Srv, "/svc", callback=lambda _req, resp: resp), ServiceServer)
    assert isinstance(wrapper.ActionClient(Action, "/action"), ActionClient)
    assert isinstance(wrapper.ActionServer(Action, "/action", execute_callback=lambda *_: None), ActionServer)


# ---------------------------------------------------------------------------
# Prefix tests — the wrapped native object's .name should reflect prefix
# ---------------------------------------------------------------------------

def test_prefix_applies_to_custom_api_names() -> None:
    wrapper = ROSWrapper(
        ROSConfig(version=ROSVersion.ROS1, auto_init=False, prefix="/module_a"),
        backend=FakeBackend(),
    )

    assert wrapper.publisher("/topic", Msg)._native.name == "/module_a/topic"
    assert wrapper.subscriber("/topic", Msg, callback=lambda _: None)._native.name == "/module_a/topic"
    assert wrapper.service_client("/svc", Srv)._native.name == "/module_a/svc"
    assert wrapper.service_server("/svc", Srv)._native.name == "/module_a/svc"
    assert wrapper.action_client("/action", Action)._native.name == "/module_a/action"
    assert wrapper.action_server("/action", Action)._native.name == "/module_a/action"
    # Already-prefixed path should not be doubled
    assert wrapper.publisher("/module_a/topic", Msg)._native.name == "/module_a/topic"


def test_prefix_applies_to_ros1_ros2_compat_names() -> None:
    wrapper = ROSWrapper(
        ROSConfig(version=ROSVersion.ROS2, auto_init=False, prefix="module_b"),
        backend=FakeBackend(),
    )

    assert wrapper.Publisher("/topic", Msg)._native.name == "/module_b/topic"
    assert wrapper.ServiceProxy("/svc", Srv)._native.name == "/module_b/svc"
    assert wrapper.SimpleActionClient("/action", Action)._native.name == "/module_b/action"

    assert wrapper.create_publisher(Msg, "/topic")._native.name == "/module_b/topic"
    assert wrapper.create_client(Srv, "/svc")._native.name == "/module_b/svc"
    assert wrapper.ActionClient(Action, "/action")._native.name == "/module_b/action"


# ---------------------------------------------------------------------------
# Decorator tests
# ---------------------------------------------------------------------------

def test_topic_decorator_inferrs_publisher_role() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    @wrapper.Topic("/topic", Msg)
    def fn(*, publisher):
        return publisher

    entity = fn()
    assert isinstance(entity, Publisher)
    assert get_ros_meta(fn)[0].decorator == "Topic"
    assert get_ros_meta(fn)[0].role == "publisher"


def test_topic_decorator_inferrs_subscriber_role() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    @wrapper.Topic("/topic", Msg, callback=lambda _msg: None)
    def fn(*, subscriber):
        return subscriber

    entity = fn()
    assert isinstance(entity, Subscriber)
    assert get_ros_meta(fn)[0].decorator == "Topic"
    assert get_ros_meta(fn)[0].role == "subscriber"


def test_topic_decorator_rejects_ambiguous_signature() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    try:
        @wrapper.Topic("/topic", Msg)
        def fn(*, publisher, subscriber):
            return publisher, subscriber
    except ROSDecoratorUsageError:
        pass
    else:
        assert False, "Expected ROSDecoratorUsageError"


def test_service_and_action_roles_are_inferred_from_signature() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    @wrapper.Service("/svc", Srv)
    def call_service(*, client):
        return client

    @wrapper.Action("/action", Action)
    def serve_action(*, server):
        return server

    assert isinstance(call_service(), ServiceClient)
    assert isinstance(serve_action(), ActionServer)
    assert get_ros_meta(call_service)[0].role == "client"
    assert get_ros_meta(serve_action)[0].role == "server"


def test_ros_meta_is_stored_only_in___ros_meta___with_tuple_append() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    @wrapper.Publish("/p", Msg)
    @wrapper.Subscribe("/s", Msg, callback=lambda _msg: None)
    def fn(*, publisher, subscriber):
        return publisher, subscriber

    _ = fn()
    assert not hasattr(fn, "ros_meta")
    assert hasattr(fn, "__ros_meta__")

    history = getattr(fn, "__ros_meta__")
    assert isinstance(history, tuple)
    assert len(history) == 2
    assert get_ros_meta(fn) == history


def test_prefix_applies_to_decorator_entity_and_meta() -> None:
    wrapper = ROSWrapper(
        ROSConfig(version=ROSVersion.ROS2, auto_init=False, prefix="/module_c"),
        backend=FakeBackend(),
    )

    @wrapper.Topic("/topic", Msg)
    def topic_fn(*, publisher):
        return publisher

    @wrapper.Service("/svc", Srv)
    def service_fn(*, client):
        return client

    topic_entity = topic_fn()
    service_entity = service_fn()
    topic_meta = get_ros_meta(topic_fn)[0]
    service_meta = get_ros_meta(service_fn)[0]

    assert isinstance(topic_entity, Publisher)
    assert isinstance(service_entity, ServiceClient)
    assert topic_entity._native.name == "/module_c/topic"
    assert service_entity._native.name == "/module_c/svc"
    assert topic_meta.resource == "/module_c/topic"
    assert service_meta.resource == "/module_c/svc"


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------

def test_spin_and_shutdown_delegate_to_backend() -> None:
    backend = FakeBackend()
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=backend)

    wrapper.spin()
    wrapper.shutdown()
    wrapper.close()

    assert backend.spin_calls == 1
    assert backend.shutdown_calls == 2


def test_init_delegates_to_backend() -> None:
    backend = FakeBackend()
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS1, auto_init=False), backend=backend)
    wrapper.init()
    assert backend.init_calls == 1


def test_string_version_is_normalized_to_enum() -> None:
    cfg = ROSConfig(version="ros2", auto_init=False)
    assert cfg.version is ROSVersion.ROS2


# ---------------------------------------------------------------------------
# clients.py unit tests — wrapper logic without real ROS
# ---------------------------------------------------------------------------

def test_service_handler_ros1_wrapping() -> None:
    """_wrap_service_handler_for_ros1 should inject a response object."""

    class FakeSrv:
        class Response:
            result = 0

        _response_class = Response

    responses = []

    def unified_handler(request: Any, response: Any) -> Any:
        response.result = request
        responses.append(response)
        return response

    ros1_handler = _wrap_service_handler_for_ros1(FakeSrv, unified_handler)
    returned = ros1_handler(42)
    assert returned.result == 42
    assert responses[0] is returned


def test_service_handler_ros2_wrapping_is_passthrough() -> None:
    sentinel = object()
    assert _wrap_service_handler_for_ros2(sentinel) is sentinel


def test_server_goal_handle_ros1_is_cancel_requested() -> None:
    class FakeServer:
        def __init__(self, preempt: bool) -> None:
            self._preempt = preempt

        def is_preempt_requested(self) -> bool:
            return self._preempt

    gh_yes = ServerGoalHandle("ros1", request=None, ros1_server=FakeServer(True))
    gh_no = ServerGoalHandle("ros1", request=None, ros1_server=FakeServer(False))
    assert gh_yes.is_cancel_requested is True
    assert gh_no.is_cancel_requested is False


def test_server_goal_handle_ros2_is_cancel_requested() -> None:
    class FakeHandle:
        def __init__(self, cancel: bool) -> None:
            self.is_cancel_requested = cancel

    gh_yes = ServerGoalHandle("ros2", request=None, ros2_goal_handle=FakeHandle(True))
    gh_no = ServerGoalHandle("ros2", request=None, ros2_goal_handle=FakeHandle(False))
    assert gh_yes.is_cancel_requested is True
    assert gh_no.is_cancel_requested is False


def test_action_execute_ros1_calls_set_succeeded() -> None:
    """_wrap_action_execute_for_ros1 should call set_succeeded with the result."""

    class FakeServer:
        def __init__(self) -> None:
            self.succeeded_result = None
            self._preempt = False

        def is_preempt_requested(self) -> bool:
            return self._preempt

        def set_succeeded(self, result: Any) -> None:
            self.succeeded_result = result

        def set_preempted(self) -> None:
            pass

    fake_server = FakeServer()
    server_ref = [fake_server]

    sentinel_result = object()

    def execute(goal_handle: ServerGoalHandle) -> Any:
        # goal_handle.request should be our goal_msg
        assert goal_handle.request == "goal_msg"
        return sentinel_result

    wrapped = _wrap_action_execute_for_ros1(server_ref, execute)
    wrapped("goal_msg")
    assert fake_server.succeeded_result is sentinel_result


def test_action_execute_ros2_wraps_goal_handle() -> None:
    """_wrap_action_execute_for_ros2 should pass a ServerGoalHandle."""

    received = []

    def execute(goal_handle: ServerGoalHandle) -> str:
        received.append(goal_handle)
        return "done"

    class FakeRos2GoalHandle:
        request = "ros2_request"

    wrapped = _wrap_action_execute_for_ros2(execute)
    result = wrapped(FakeRos2GoalHandle())
    assert result == "done"
    assert isinstance(received[0], ServerGoalHandle)
    assert received[0].request == "ros2_request"
