class ROSWrapperError(Exception):
    """Base exception for this package."""


class ROSRuntimeUnavailableError(ROSWrapperError):
    """Raised when required ROS runtime modules are unavailable."""


class ROSDecoratorUsageError(ROSWrapperError):
    """Raised when decorator usage does not match required signature/role."""
