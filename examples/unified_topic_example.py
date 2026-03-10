"""
统一 Topic API 示例

演示如何使用 ros-wrapper 统一的 Topic Publisher 和 Subscriber API，
支持在 ROS1 和 ROS2 之间无缝切换。
"""

from ros_wrapper import ROSVersion, ROSWrapper


# 模拟消息类型（实际使用时替换为真实的消息类型）
class String:
    """模拟 std_msgs.msg.String"""

    def __init__(self, data: str = "") -> None:
        self.data = data


def example_unified_api() -> None:
    """示例 1: 使用自定义统一 API (推荐)"""
    print("\n=== 示例 1: 自定义统一 API ===")

    # 创建 ROS2 wrapper（切换到 ROS1 只需改变版本参数）
    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="unified_topic_demo", auto_init=False
    )

    try:
        # 创建 Publisher - 统一的参数顺序和命名
        publisher = wrapper.publisher("/chatter", String)
        print(f"Created publisher: {publisher}")

        # 创建 Subscriber - 使用关键字参数 callback
        def callback(msg: String) -> None:
            print(f"Received: {msg.data}")

        subscriber = wrapper.subscriber("/chatter", String, callback=callback)
        print(f"Created subscriber: {subscriber}")

        # 发布消息
        message = String(data="Hello from unified API!")
        print(f"Publishing: {message.data}")
        # publisher.publish(message)  # 需要真实 ROS 环境

    finally:
        wrapper.close()


def example_ros1_compatible_api() -> None:
    """示例 2: 使用 ROS1 兼容 API"""
    print("\n=== 示例 2: ROS1 兼容 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS1, node_name="ros1_compat_demo", auto_init=False
    )

    try:
        # 完全兼容 rospy.Publisher 语法
        publisher = wrapper.Publisher("/chatter", String, queue_size=10)
        print(f"Created ROS1-style publisher: {publisher}")

        # 完全兼容 rospy.Subscriber 语法
        def callback(msg: String) -> None:
            print(f"Received: {msg.data}")

        subscriber = wrapper.Subscriber("/chatter", String, callback, queue_size=10)
        print(f"Created ROS1-style subscriber: {subscriber}")

    finally:
        wrapper.close()


def example_ros2_compatible_api() -> None:
    """示例 3: 使用 ROS2 兼容 API"""
    print("\n=== 示例 3: ROS2 兼容 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="ros2_compat_demo", auto_init=False
    )

    try:
        # 完全兼容 node.create_publisher 语法
        # 注意: msg_type 在前, topic 在后 (ROS2 风格)
        publisher = wrapper.create_publisher(String, "/chatter", qos_profile=10)
        print(f"Created ROS2-style publisher: {publisher}")

        # 完全兼容 node.create_subscription 语法
        def callback(msg: String) -> None:
            print(f"Received: {msg.data}")

        subscriber = wrapper.create_subscription(
            String, "/chatter", callback, qos_profile=10
        )
        print(f"Created ROS2-style subscriber: {subscriber}")

    finally:
        wrapper.close()


def example_decorator_auto_inference() -> None:
    """示例 4: 使用装饰器自动推断角色"""
    print("\n=== 示例 4: 装饰器自动推断角色 ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="decorator_demo", auto_init=False
    )

    # 根据函数参数名自动推断为 Publisher
    @wrapper.Topic("/output", String)
    def send_message(*, publisher) -> None:
        """函数参数包含 'publisher'，自动注入 Publisher"""
        message = String(data="Hello from decorator!")
        print(f"Publishing via decorator: {message.data}")
        # publisher.publish(message)  # 需要真实 ROS 环境

    # 根据函数参数名自动推断为 Subscriber
    @wrapper.Topic("/input", String, callback=lambda msg: None)
    def receive_message(*, subscriber) -> None:
        """函数参数包含 'subscriber'，自动注入 Subscriber"""
        print(f"Subscriber injected: {subscriber}")

    # 调用函数时自动创建 ROS 实体
    send_message()
    receive_message()

    # 查看元信息
    from ros_wrapper import get_ros_meta

    meta1 = get_ros_meta(send_message)[0]
    print(f"\nsend_message 元信息:")
    print(f"  - decorator: {meta1.decorator}")
    print(f"  - role: {meta1.role}")
    print(f"  - resource: {meta1.resource}")
    print(f"  - ros_type: {meta1.ros_type}")

    meta2 = get_ros_meta(receive_message)[0]
    print(f"\nreceive_message 元信息:")
    print(f"  - decorator: {meta2.decorator}")
    print(f"  - role: {meta2.role}")
    print(f"  - resource: {meta2.resource}")

    wrapper.close()


def example_decorator_explicit() -> None:
    """示例 5: 使用显式装饰器"""
    print("\n=== 示例 5: 显式装饰器 ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="explicit_decorator_demo", auto_init=False
    )

    # 显式指定为 Publisher
    @wrapper.Publish("/status", String)
    def publish_status(*, publisher) -> None:
        """使用 @Publish 显式指定为发布者"""
        status = String(data="System running")
        print(f"Publishing status: {status.data}")
        # publisher.publish(status)

    # 显式指定为 Subscriber
    @wrapper.Subscribe("/commands", String, callback=lambda msg: print(msg.data))
    def handle_commands(*, subscriber) -> None:
        """使用 @Subscribe 显式指定为订阅者"""
        print(f"Command subscriber ready: {subscriber}")

    publish_status()
    handle_commands()

    wrapper.close()


def example_with_prefix() -> None:
    """示例 6: 使用命名空间前缀"""
    print("\n=== 示例 6: 使用命名空间前缀 ===")

    # 为模块添加统一前缀
    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2,
        node_name="prefixed_demo",
        prefix="/robot_a",
        auto_init=False,
    )

    try:
        # 实际使用的 topic 名称为 /robot_a/sensors/temperature
        publisher = wrapper.publisher("/sensors/temperature", String)
        print(f"Publisher with prefix: {publisher}")
        # 从返回的 tuple 可以看到实际使用的 topic 名称

        # 装饰器也会自动应用前缀
        @wrapper.Topic("/sensors/pressure", String)
        def publish_pressure(*, publisher) -> None:
            print(f"Publisher with prefix from decorator: {publisher}")

        publish_pressure()

        # 检查元信息中的实际路径
        from ros_wrapper import get_ros_meta

        meta = get_ros_meta(publish_pressure)[0]
        print(f"Actual resource path: {meta.resource}")  # /robot_a/sensors/pressure

    finally:
        wrapper.close()


def example_multi_version_compatibility() -> None:
    """示例 7: 同一代码支持多版本"""
    print("\n=== 示例 7: 同一代码支持多版本 ===")

    def create_node(ros_version: ROSVersion) -> None:
        """同一函数可以支持不同 ROS 版本"""
        wrapper = ROSWrapper.from_version(
            ros_version, node_name=f"multi_version_{ros_version.value}", auto_init=False
        )

        try:
            # 使用统一 API，不需要关心底层版本
            pub = wrapper.publisher("/data", String)
            sub = wrapper.subscriber("/data", String, callback=lambda msg: None)

            print(f"\n{ros_version.value} 环境:")
            print(f"  Publisher: {pub}")
            print(f"  Subscriber: {sub}")

        finally:
            wrapper.close()

    # 同一代码可以运行在不同版本
    create_node(ROSVersion.ROS1)
    create_node(ROSVersion.ROS2)


def main() -> None:
    """运行所有示例"""
    print("=" * 60)
    print("ROS Wrapper - 统一 Topic API 示例")
    print("=" * 60)

    example_unified_api()
    example_ros1_compatible_api()
    example_ros2_compatible_api()
    example_decorator_auto_inference()
    example_decorator_explicit()
    example_with_prefix()
    example_multi_version_compatibility()

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
