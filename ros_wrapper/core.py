from __future__ import annotations

import inspect
from typing import Any, Callable

from ros_wrapper.backends import ROSBackend, create_backend
from ros_wrapper.config import ROSConfig, ROSVersion
from ros_wrapper.exceptions import ROSDecoratorUsageError
from ros_wrapper.meta import ROSMeta, attach_ros_meta, resolve_type_name, with_injection


class ROSWrapper:
    """Facade exposing custom and native-compatible ROS APIs."""

    def __init__(self, config: ROSConfig, backend: ROSBackend | None = None) -> None:
        self.config = config
        self.backend = backend or create_backend(config)

    @property
    def backend_version(self) -> ROSVersion:
        return self.backend.version

    @classmethod
    def from_version(
        cls,
        version: ROSVersion,
        *,
        node_name: str = "ros_wrapper_node",
        namespace: str = "",
        prefix: str = "",
        auto_init: bool = True,
        **backend_kwargs: Any,
    ) -> "ROSWrapper":
        config = ROSConfig(
            version=version,
            node_name=node_name,
            namespace=namespace,
            prefix=prefix,
            auto_init=auto_init,
            backend_kwargs=backend_kwargs,
        )
        return cls(config)

    # Custom API
    def publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Any:
        return self.backend.publisher(self._with_prefix(topic), msg_type, **kwargs)

    def subscriber(
        self,
        topic: str,
        msg_type: Any,
        *,
        callback: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        callback = callback or (lambda _msg: None)
        return self.backend.subscriber(
            self._with_prefix(topic),
            msg_type,
            callback,
            **kwargs,
        )

    def service_client(self, name: str, srv_type: Any, **kwargs: Any) -> Any:
        return self.backend.service_client(self._with_prefix(name), srv_type, **kwargs)

    def service_server(
        self,
        name: str,
        srv_type: Any,
        *,
        handler: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        handler = handler or self._default_service_handler()
        return self.backend.service_server(
            self._with_prefix(name),
            srv_type,
            handler,
            **kwargs,
        )

    def action_client(self, name: str, action_type: Any, **kwargs: Any) -> Any:
        return self.backend.action_client(self._with_prefix(name), action_type, **kwargs)

    def action_server(
        self,
        name: str,
        action_type: Any,
        *,
        execute_callback: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        execute_callback = execute_callback or self._default_action_execute()
        return self.backend.action_server(
            self._with_prefix(name),
            action_type,
            execute_callback,
            **kwargs,
        )

    def service(self, name: str, srv_type: Any, role: str, **kwargs: Any) -> Any:
        normalized = role.lower()
        if normalized == "client":
            return self.service_client(name, srv_type, **kwargs)
        if normalized == "server":
            return self.service_server(name, srv_type, **kwargs)
        raise ValueError("role must be 'client' or 'server'")

    def action(self, name: str, action_type: Any, role: str, **kwargs: Any) -> Any:
        normalized = role.lower()
        if normalized == "client":
            return self.action_client(name, action_type, **kwargs)
        if normalized == "server":
            return self.action_server(name, action_type, **kwargs)
        raise ValueError("role must be 'client' or 'server'")

    # ROS1-compatible API
    def Publisher(self, topic: str, msg_type: Any, **kwargs: Any) -> Any:
        return self.publisher(topic, msg_type, **kwargs)

    def Subscriber(
        self,
        topic: str,
        msg_type: Any,
        callback: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.subscriber(topic, msg_type, callback=callback, **kwargs)

    def ServiceProxy(self, name: str, srv_type: Any, **kwargs: Any) -> Any:
        return self.service_client(name, srv_type, **kwargs)

    def SimpleActionClient(self, name: str, action_type: Any, **kwargs: Any) -> Any:
        return self.action_client(name, action_type, **kwargs)

    def SimpleActionServer(
        self,
        name: str,
        action_type: Any,
        execute_cb: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.action_server(
            name,
            action_type,
            execute_callback=execute_cb,
            **kwargs,
        )

    # ROS2-compatible API
    def create_publisher(
        self,
        msg_type: Any,
        topic: str,
        qos_profile: Any = 10,
        **kwargs: Any,
    ) -> Any:
        return self.publisher(topic, msg_type, qos_profile=qos_profile, **kwargs)

    def create_subscription(
        self,
        msg_type: Any,
        topic: str,
        callback: Callable[..., Any] | None,
        qos_profile: Any = 10,
        **kwargs: Any,
    ) -> Any:
        return self.subscriber(
            topic,
            msg_type,
            callback=callback,
            qos_profile=qos_profile,
            **kwargs,
        )

    def create_client(self, srv_type: Any, name: str, **kwargs: Any) -> Any:
        return self.service_client(name, srv_type, **kwargs)

    def create_service(
        self,
        srv_type: Any,
        name: str,
        callback: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.service_server(name, srv_type, handler=callback, **kwargs)

    def ActionClient(self, action_type: Any, name: str, **kwargs: Any) -> Any:
        return self.action_client(name, action_type, **kwargs)

    def ActionServer(
        self,
        action_type: Any,
        name: str,
        execute_callback: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.action_server(
            name,
            action_type,
            execute_callback=execute_callback,
            **kwargs,
        )

    # Decorator API
    def Topic(
        self,
        topic: str,
        msg_type: Any,
        *,
        callback: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            resolved_topic = self._with_prefix(topic)
            role, inject_key = self._infer_topic_role(func)
            options = dict(kwargs)
            if role == "publisher":
                creator = lambda: self.publisher(topic, msg_type, **options)
            else:
                cb = options.pop("callback", callback)
                cb = cb or (lambda _msg: None)
                creator = lambda: self.subscriber(
                    topic,
                    msg_type,
                    callback=cb,
                    **options,
                )
            wrapped = with_injection(func, inject_key=inject_key, create_entity=creator)
            return attach_ros_meta(
                wrapped,
                ROSMeta(
                    decorator="Topic",
                    backend=self.backend_version,
                    role=role,
                    resource=resolved_topic,
                    ros_type=resolve_type_name(msg_type),
                    inject_as=inject_key,
                ),
            )

        return decorator

    def Publish(
        self,
        topic: str,
        msg_type: Any,
        *,
        inject_as: str = "publisher",
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            resolved_topic = self._with_prefix(topic)
            wrapped = with_injection(
                func,
                inject_key=inject_as,
                create_entity=lambda: self.publisher(topic, msg_type, **dict(kwargs)),
            )
            return attach_ros_meta(
                wrapped,
                ROSMeta(
                    decorator="Publish",
                    backend=self.backend_version,
                    role="publisher",
                    resource=resolved_topic,
                    ros_type=resolve_type_name(msg_type),
                    inject_as=inject_as,
                ),
            )

        return decorator

    def Subscribe(
        self,
        topic: str,
        msg_type: Any,
        *,
        callback: Callable[..., Any] | None = None,
        inject_as: str = "subscriber",
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            resolved_topic = self._with_prefix(topic)
            cb = callback or (lambda _msg: None)
            wrapped = with_injection(
                func,
                inject_key=inject_as,
                create_entity=lambda: self.subscriber(
                    topic,
                    msg_type,
                    callback=cb,
                    **dict(kwargs),
                ),
            )
            return attach_ros_meta(
                wrapped,
                ROSMeta(
                    decorator="Subscribe",
                    backend=self.backend_version,
                    role="subscriber",
                    resource=resolved_topic,
                    ros_type=resolve_type_name(msg_type),
                    inject_as=inject_as,
                ),
            )

        return decorator

    def Service(
        self,
        name: str,
        srv_type: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if args:
            if len(args) != 1 or not callable(args[0]):
                raise TypeError(
                    "Service(name, srv_type, handler) accepts exactly one callable handler "
                    "as the third positional argument."
                )
            return self.service_server(name, srv_type, handler=args[0], **kwargs)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            resolved_name = self._with_prefix(name)
            role, inject_key = self._infer_client_server_role(func)
            options = dict(kwargs)
            if role == "client":
                creator = lambda: self.service_client(name, srv_type, **options)
            else:
                server_handler = options.pop("handler", self._default_service_handler())
                creator = lambda: self.service_server(
                    name,
                    srv_type,
                    handler=server_handler,
                    **options,
                )
            wrapped = with_injection(func, inject_key=inject_key, create_entity=creator)
            return attach_ros_meta(
                wrapped,
                ROSMeta(
                    decorator="Service",
                    backend=self.backend_version,
                    role=role,
                    resource=resolved_name,
                    ros_type=resolve_type_name(srv_type),
                    inject_as=inject_key,
                ),
            )

        return decorator

    def Action(
        self,
        name: str,
        action_type: Any,
        **kwargs: Any,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            resolved_name = self._with_prefix(name)
            role, inject_key = self._infer_client_server_role(func)
            options = dict(kwargs)
            if role == "client":
                creator = lambda: self.action_client(name, action_type, **options)
            else:
                execute_callback = options.pop(
                    "execute_callback",
                    self._default_action_execute(),
                )
                creator = lambda: self.action_server(
                    name,
                    action_type,
                    execute_callback=execute_callback,
                    **options,
                )
            wrapped = with_injection(func, inject_key=inject_key, create_entity=creator)
            return attach_ros_meta(
                wrapped,
                ROSMeta(
                    decorator="Action",
                    backend=self.backend_version,
                    role=role,
                    resource=resolved_name,
                    ros_type=resolve_type_name(action_type),
                    inject_as=inject_key,
                ),
            )

        return decorator

    def init(self) -> None:
        self.backend.init()

    def spin(self) -> None:
        self.backend.spin()

    def shutdown(self) -> None:
        self.backend.shutdown()

    def close(self) -> None:
        self.shutdown()

    def __enter__(self) -> "ROSWrapper":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _infer_client_server_role(self, func: Callable[..., Any]) -> tuple[str, str]:
        params = inspect.signature(func).parameters
        has_client = "client" in params
        has_server = "server" in params
        if has_client and has_server:
            raise ROSDecoratorUsageError(
                f"{func.__name__} contains both 'client' and 'server'. Keep only one."
            )
        if has_client:
            return "client", "client"
        if has_server:
            return "server", "server"
        raise ROSDecoratorUsageError(
            f"{func.__name__} must declare either a 'client' or 'server' parameter "
            "for Service/Action decorators."
        )

    def _infer_topic_role(self, func: Callable[..., Any]) -> tuple[str, str]:
        params = inspect.signature(func).parameters
        has_publisher = "publisher" in params
        has_subscriber = "subscriber" in params
        if has_publisher and has_subscriber:
            raise ROSDecoratorUsageError(
                f"{func.__name__} contains both 'publisher' and 'subscriber'. Keep only one."
            )
        if has_publisher:
            return "publisher", "publisher"
        if has_subscriber:
            return "subscriber", "subscriber"
        raise ROSDecoratorUsageError(
            f"{func.__name__} must declare either a 'publisher' or 'subscriber' parameter "
            "for Topic decorator."
        )

    def _with_prefix(self, name: str) -> str:
        prefix = self.config.prefix.strip().strip("/")
        if not prefix:
            return name

        raw = name.strip()
        if not raw:
            return f"/{prefix}"

        is_absolute = raw.startswith("/")
        path = raw.strip("/")
        if path == prefix or path.startswith(f"{prefix}/"):
            return raw

        if is_absolute:
            return f"/{prefix}/{path}" if path else f"/{prefix}"
        return f"{prefix}/{path}" if path else prefix

    def _default_service_handler(self) -> Callable[..., Any]:
        if self.backend_version is ROSVersion.ROS2:
            return lambda _request, response: response
        return lambda _request: None

    def _default_action_execute(self) -> Callable[..., Any]:
        return lambda *_args, **_kwargs: None


def create_wrapper(config: ROSConfig) -> ROSWrapper:
    return ROSWrapper(config=config)
