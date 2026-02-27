from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ROSVersion(str, Enum):
    ROS1 = "ROS1"
    ROS2 = "ROS2"


@dataclass(frozen=True)
class ROSConfig:
    """Configuration for selecting and creating a ROS runtime backend."""

    version: ROSVersion
    node_name: str = "ros_wrapper_node"
    namespace: str = ""
    prefix: str = ""
    auto_init: bool = True
    backend_kwargs: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized = self._normalize_version(self.version)
        object.__setattr__(self, "version", normalized)
        if normalized is ROSVersion.ROS2 and not self.auto_init:
            # ROS2 needs an initialized context/node for entity creation.
            object.__setattr__(self, "auto_init", True)

    def normalized_version(self) -> ROSVersion:
        return self.version

    @staticmethod
    def _normalize_version(version: ROSVersion | str) -> ROSVersion:
        if isinstance(version, ROSVersion):
            return version
        try:
            return ROSVersion(version.upper())
        except ValueError as exc:
            raise ValueError(f"Unsupported ROS version: {version!r}") from exc
