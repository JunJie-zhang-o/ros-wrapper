"""Mode 1 demo: direct entity factory API."""

from ros_wrapper import ROSVersion, ROSWrapper


class String:
    """Stub message type for offline demo."""


def main() -> None:
    wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="mode1_demo", auto_init=False)
    try:
        # Requires real ROS runtime and message definitions when executed in production.
        _publisher = wrapper.publisher("/demo", String)
        _subscriber = wrapper.subscriber("/demo", String)
        print("Mode1 entities created")
    finally:
        wrapper.close()


if __name__ == "__main__":
    main()
