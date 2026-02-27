from __future__ import annotations

from typing import Any

from ros_wrapper import ROSConfig, ROSVersion, ROSWrapper, get_ros_meta
from ros_wrapper.backends.base import ROSBackend
from ros_wrapper.exceptions import ROSDecoratorUsageError


class FakeBackend(ROSBackend):
    version = ROSVersion.ROS2

    def __init__(self) -> None:
        self.init_calls = 0
        self.spin_calls = 0
        self.shutdown_calls = 0

    def publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Any:
        return ("publisher", topic, msg_type, kwargs)

    def subscriber(
        self,
        topic: str,
        msg_type: Any,
        callback: Any,
        **kwargs: Any,
    ) -> Any:
        return ("subscriber", topic, msg_type, callback, kwargs)

    def service_client(self, name: str, srv_type: Any, **kwargs: Any) -> Any:
        return ("service_client", name, srv_type, kwargs)

    def service_server(
        self,
        name: str,
        srv_type: Any,
        handler: Any,
        **kwargs: Any,
    ) -> Any:
        return ("service_server", name, srv_type, handler, kwargs)

    def action_client(self, name: str, action_type: Any, **kwargs: Any) -> Any:
        return ("action_client", name, action_type, kwargs)

    def action_server(
        self,
        name: str,
        action_type: Any,
        execute_callback: Any,
        **kwargs: Any,
    ) -> Any:
        return ("action_server", name, action_type, execute_callback, kwargs)

    def init(self) -> None:
        self.init_calls += 1

    def spin(self) -> None:
        self.spin_calls += 1

    def shutdown(self) -> None:
        self.shutdown_calls += 1


class Msg:
    pass


class Srv:
    pass


class Action:
    pass


def test_ros2_config_forces_auto_init_true() -> None:
    cfg = ROSConfig(version=ROSVersion.ROS2, auto_init=False)
    assert cfg.auto_init is True


def test_ros1_config_respects_auto_init_flag() -> None:
    cfg = ROSConfig(version=ROSVersion.ROS1, auto_init=False)
    assert cfg.auto_init is False


def test_custom_api_methods_route_to_backend() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS1, auto_init=False), backend=FakeBackend())

    assert wrapper.publisher("/topic", Msg)[0] == "publisher"
    assert wrapper.subscriber("/topic", Msg, callback=lambda _msg: None)[0] == "subscriber"
    assert wrapper.service_client("/svc", Srv)[0] == "service_client"
    assert wrapper.service_server("/svc", Srv)[0] == "service_server"
    assert wrapper.action_client("/action", Action)[0] == "action_client"
    assert wrapper.action_server("/action", Action)[0] == "action_server"


def test_ros1_compat_api_methods_route_to_custom_api() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS1, auto_init=False), backend=FakeBackend())

    assert wrapper.Publisher("/topic", Msg)[0] == "publisher"
    assert wrapper.Subscriber("/topic", Msg, callback=lambda _msg: None)[0] == "subscriber"
    assert wrapper.ServiceProxy("/svc", Srv)[0] == "service_client"
    assert wrapper.Service("/svc", Srv, lambda _req: None)[0] == "service_server"
    assert wrapper.SimpleActionClient("/action", Action)[0] == "action_client"
    assert wrapper.SimpleActionServer("/action", Action, execute_cb=lambda *_: None)[0] == "action_server"


def test_ros2_compat_api_methods_route_to_custom_api() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    pub = wrapper.create_publisher(Msg, "/topic", qos_profile=5)
    sub = wrapper.create_subscription(Msg, "/topic", callback=lambda _msg: None, qos_profile=7)
    client = wrapper.create_client(Srv, "/svc")
    server = wrapper.create_service(Srv, "/svc", callback=lambda _req, resp: resp)
    act_client = wrapper.ActionClient(Action, "/action")
    act_server = wrapper.ActionServer(Action, "/action", execute_callback=lambda *_: None)

    assert pub == ("publisher", "/topic", Msg, {"qos_profile": 5})
    assert sub[0] == "subscriber"
    assert sub[4]["qos_profile"] == 7
    assert client[0] == "service_client"
    assert server[0] == "service_server"
    assert act_client[0] == "action_client"
    assert act_server[0] == "action_server"


def test_prefix_applies_to_custom_api_names() -> None:
    wrapper = ROSWrapper(
        ROSConfig(version=ROSVersion.ROS1, auto_init=False, prefix="/module_a"),
        backend=FakeBackend(),
    )

    assert wrapper.publisher("/topic", Msg)[1] == "/module_a/topic"
    assert wrapper.subscriber("/topic", Msg, callback=lambda _msg: None)[1] == "/module_a/topic"
    assert wrapper.service_client("/svc", Srv)[1] == "/module_a/svc"
    assert wrapper.service_server("/svc", Srv)[1] == "/module_a/svc"
    assert wrapper.action_client("/action", Action)[1] == "/module_a/action"
    assert wrapper.action_server("/action", Action)[1] == "/module_a/action"
    assert wrapper.publisher("/module_a/topic", Msg)[1] == "/module_a/topic"


def test_prefix_applies_to_ros1_ros2_compat_names() -> None:
    wrapper = ROSWrapper(
        ROSConfig(version=ROSVersion.ROS2, auto_init=False, prefix="module_b"),
        backend=FakeBackend(),
    )

    assert wrapper.Publisher("/topic", Msg)[1] == "/module_b/topic"
    assert wrapper.ServiceProxy("/svc", Srv)[1] == "/module_b/svc"
    assert wrapper.SimpleActionClient("/action", Action)[1] == "/module_b/action"

    assert wrapper.create_publisher(Msg, "/topic")[1] == "/module_b/topic"
    assert wrapper.create_client(Srv, "/svc")[1] == "/module_b/svc"
    assert wrapper.ActionClient(Action, "/action")[1] == "/module_b/action"


def test_topic_decorator_inferrs_publisher_role() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    @wrapper.Topic("/topic", Msg)
    def fn(*, publisher):
        return publisher

    entity = fn()
    assert entity[0] == "publisher"
    assert get_ros_meta(fn)[0].decorator == "Topic"
    assert get_ros_meta(fn)[0].role == "publisher"


def test_topic_decorator_inferrs_subscriber_role() -> None:
    wrapper = ROSWrapper(ROSConfig(version=ROSVersion.ROS2, auto_init=False), backend=FakeBackend())

    @wrapper.Topic("/topic", Msg, callback=lambda _msg: None)
    def fn(*, subscriber):
        return subscriber

    entity = fn()
    assert entity[0] == "subscriber"
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

    assert call_service()[0] == "service_client"
    assert serve_action()[0] == "action_server"
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

    assert topic_entity[1] == "/module_c/topic"
    assert service_entity[1] == "/module_c/svc"
    assert topic_meta.resource == "/module_c/topic"
    assert service_meta.resource == "/module_c/svc"


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
