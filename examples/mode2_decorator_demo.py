"""Mode 2 demo: decorator injection + ros_meta."""

from ros_wrapper import ROSVersion, ROSWrapper, get_ros_meta


class String:
    """Stub message type for offline demo."""


def main() -> None:
    wrapper = ROSWrapper.from_version(ROSVersion.ROS1, node_name="mode2_demo", auto_init=False)

    @wrapper.Publish("/demo", String)
    def publish_once(*, publisher):
        print("injected publisher:", publisher)

    publish_once()
    print(get_ros_meta(publish_once))


if __name__ == "__main__":
    main()
