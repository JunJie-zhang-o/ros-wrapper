from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import wraps
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class ROSMeta:
    decorator: str
    backend: str
    role: str
    resource: str
    ros_type: str
    inject_as: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def resolve_type_name(ros_type: Any) -> str:
    module = getattr(ros_type, "__module__", None)
    name = getattr(ros_type, "__name__", None)
    if module and name:
        return f"{module}.{name}"
    return repr(ros_type)


def attach_ros_meta(func: Callable[..., Any], meta: ROSMeta) -> Callable[..., Any]:
    history = list(getattr(func, "__ros_meta__", ()))
    history.append(meta)
    setattr(func, "__ros_meta__", tuple(history))
    return func


def with_injection(
    func: Callable[..., Any],
    *,
    inject_key: str,
    create_entity: Callable[[], Any],
) -> Callable[..., Any]:
    cache: dict[str, Any] = {"entity": None}

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if cache["entity"] is None:
            cache["entity"] = create_entity()
        kwargs.setdefault(inject_key, cache["entity"])
        return func(*args, **kwargs)

    return wrapper


def get_ros_meta(target: Callable[..., Any]) -> tuple[ROSMeta, ...]:
    return tuple(getattr(target, "__ros_meta__", ()))


def iter_ros_meta(targets: Iterable[Callable[..., Any]]) -> dict[str, tuple[ROSMeta, ...]]:
    return {getattr(fn, "__name__", "<anonymous>"): get_ros_meta(fn) for fn in targets}
