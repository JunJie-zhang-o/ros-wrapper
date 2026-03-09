"""
统一 Action API 示例

演示如何使用 ros-wrapper 统一的 Action Client 和 Server API，
支持在 ROS1 和 ROS2 之间无缝切换。
"""

from typing import Any

from ros_wrapper import ROSVersion, ROSWrapper


# 模拟动作类型（实际使用时替换为真实的动作类型）
class Fibonacci:
    """模拟 example_interfaces.action.Fibonacci"""

    class Goal:
        def __init__(self, order: int = 0) -> None:
            self.order = order

    class Result:
        def __init__(self) -> None:
            self.sequence = []

    class Feedback:
        def __init__(self) -> None:
            self.partial_sequence = []


def example_unified_api() -> None:
    """示例 1: 使用自定义统一 API (推荐)"""
    print("\n=== 示例 1: 自定义统一 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="unified_action_demo", auto_init=False
    )

    try:
        # 创建 Action Client - 统一的参数顺序
        client = wrapper.action_client("/fibonacci", Fibonacci)
        print(f"Created action client: {client}")

        # 创建 Action Server - 使用关键字参数 execute_callback
        def execute_callback(goal: Any) -> Any:
            """执行动作的回调函数"""
            result = Fibonacci.Result()
            # 计算斐波那契数列
            result.sequence = [0, 1]
            for i in range(2, goal.order):
                result.sequence.append(result.sequence[i - 1] + result.sequence[i - 2])
            return result

        server = wrapper.action_server(
            "/fibonacci", Fibonacci, execute_callback=execute_callback
        )
        print(f"Created action server: {server}")

        # 发送目标（需要真实 ROS 环境）
        # goal = Fibonacci.Goal(order=10)
        # client.send_goal(goal)

    finally:
        wrapper.close()


def example_ros1_compatible_api() -> None:
    """示例 2: 使用 ROS1 兼容 API"""
    print("\n=== 示例 2: ROS1 兼容 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS1, node_name="ros1_action_demo", auto_init=False
    )

    try:
        # 完全兼容 actionlib.SimpleActionClient 语法
        client = wrapper.SimpleActionClient("/fibonacci", Fibonacci)
        print(f"Created ROS1-style action client: {client}")

        # 完全兼容 actionlib.SimpleActionServer 语法
        def execute_cb(goal: Any) -> None:
            """ROS1 风格的执行回调"""
            print(f"Executing goal: order={goal.order}")
            # 执行动作逻辑

        server = wrapper.SimpleActionServer("/fibonacci", Fibonacci, execute_cb=execute_cb)
        print(f"Created ROS1-style action server: {server}")

    finally:
        wrapper.close()


def example_ros2_compatible_api() -> None:
    """示例 3: 使用 ROS2 兼容 API"""
    print("\n=== 示例 3: ROS2 兼容 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="ros2_action_demo", auto_init=False
    )

    try:
        # 完全兼容 rclpy.action.ActionClient 语法
        # 注意: action_type 在前, name 在后 (ROS2 风格)
        client = wrapper.ActionClient(Fibonacci, "/fibonacci")
        print(f"Created ROS2-style action client: {client}")

        # 完全兼容 rclpy.action.ActionServer 语法
        def execute_callback(goal_handle: Any) -> Any:
            """ROS2 风格的执行回调"""
            result = Fibonacci.Result()
            print(f"Executing goal: order={goal_handle.request.order}")
            return result

        server = wrapper.ActionServer(
            Fibonacci, "/fibonacci", execute_callback=execute_callback
        )
        print(f"Created ROS2-style action server: {server}")

    finally:
        wrapper.close()


def example_decorator_auto_inference() -> None:
    """示例 4: 使用装饰器自动推断角色"""
    print("\n=== 示例 4: 装饰器自动推断角色 ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="action_decorator_demo", auto_init=False
    )

    # 根据函数参数名 'client' 自动推断为 Action Client
    @wrapper.Action("/move_robot", Fibonacci)
    def request_movement(*, client) -> None:
        """函数参数包含 'client'，自动注入 Action Client"""
        print(f"Action client injected: {client}")
        # goal = Fibonacci.Goal(order=10)
        # client.send_goal(goal)

    # 根据函数参数名 'server' 自动推断为 Action Server
    @wrapper.Action("/move_robot", Fibonacci)
    def handle_movement(*, server) -> None:
        """函数参数包含 'server'，自动注入 Action Server"""
        print(f"Action server injected: {server}")

    # 调用函数时自动创建 ROS 实体
    request_movement()
    handle_movement()

    # 查看元信息
    from ros_wrapper import get_ros_meta

    meta1 = get_ros_meta(request_movement)[0]
    print(f"\nrequest_movement 元信息:")
    print(f"  - decorator: {meta1.decorator}")
    print(f"  - role: {meta1.role}")
    print(f"  - resource: {meta1.resource}")

    meta2 = get_ros_meta(handle_movement)[0]
    print(f"\nhandle_movement 元信息:")
    print(f"  - decorator: {meta2.decorator}")
    print(f"  - role: {meta2.role}")
    print(f"  - resource: {meta2.resource}")

    wrapper.close()


def example_with_prefix() -> None:
    """示例 5: 使用命名空间前缀"""
    print("\n=== 示例 5: 使用命名空间前缀 ===")

    # 为模块添加统一前缀
    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2,
        node_name="prefixed_action_demo",
        prefix="/robot_a",
        auto_init=False,
    )

    try:
        # 实际使用的动作名称为 /robot_a/navigation/move_to_goal
        client = wrapper.action_client("/navigation/move_to_goal", Fibonacci)
        print(f"Action client with prefix: {client}")

        # 装饰器也会自动应用前缀
        @wrapper.Action("/navigation/go_home", Fibonacci)
        def go_home(*, client) -> None:
            print(f"Action client with prefix from decorator: {client}")

        go_home()

        # 检查元信息中的实际路径
        from ros_wrapper import get_ros_meta

        meta = get_ros_meta(go_home)[0]
        print(f"Actual resource path: {meta.resource}")  # /robot_a/navigation/go_home

    finally:
        wrapper.close()


def example_complex_action_server() -> None:
    """示例 6: 复杂的 Action Server 实现"""
    print("\n=== 示例 6: 复杂的 Action Server 实现 ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="complex_action_demo", auto_init=False
    )

    def execute_fibonacci(goal: Any) -> Any:
        """
        完整的斐波那契数列 Action Server 实现
        支持反馈和结果
        """
        print(f"Received goal: order={goal.order}")

        result = Fibonacci.Result()
        feedback = Fibonacci.Feedback()

        # 计算斐波那契数列
        sequence = [0, 1]
        feedback.partial_sequence = sequence

        for i in range(2, goal.order):
            # 检查是否取消（需要真实 ROS 环境）
            # if goal_handle.is_cancel_requested:
            #     goal_handle.canceled()
            #     return result

            sequence.append(sequence[i - 1] + sequence[i - 2])
            feedback.partial_sequence = sequence

            # 发布反馈（需要真实 ROS 环境）
            # goal_handle.publish_feedback(feedback)

            print(f"Progress: {len(sequence)}/{goal.order}")

        result.sequence = sequence
        print(f"Goal succeeded: {result.sequence}")
        return result

    try:
        server = wrapper.action_server(
            "/fibonacci", Fibonacci, execute_callback=execute_fibonacci
        )
        print(f"Complex action server created: {server}")

    finally:
        wrapper.close()


def example_multi_version_compatibility() -> None:
    """示例 7: 同一代码支持多版本"""
    print("\n=== 示例 7: 同一代码支持多版本 ===")

    def create_action_node(ros_version: ROSVersion) -> None:
        """同一函数可以支持不同 ROS 版本"""
        wrapper = ROSWrapper.from_version(
            ros_version,
            node_name=f"action_multi_version_{ros_version.value}",
            auto_init=False,
        )

        try:
            # 使用统一 API，不需要关心底层版本
            client = wrapper.action_client("/compute", Fibonacci)

            def execute_callback(goal: Any) -> Any:
                result = Fibonacci.Result()
                result.sequence = [0, 1]
                for i in range(2, 10):
                    result.sequence.append(
                        result.sequence[i - 1] + result.sequence[i - 2]
                    )
                return result

            server = wrapper.action_server(
                "/compute", Fibonacci, execute_callback=execute_callback
            )

            print(f"\n{ros_version.value} 环境:")
            print(f"  Client: {client}")
            print(f"  Server: {server}")

        finally:
            wrapper.close()

    # 同一代码可以运行在不同版本
    create_action_node(ROSVersion.ROS1)
    create_action_node(ROSVersion.ROS2)


def main() -> None:
    """运行所有示例"""
    print("=" * 60)
    print("ROS Wrapper - 统一 Action API 示例")
    print("=" * 60)

    example_unified_api()
    example_ros1_compatible_api()
    example_ros2_compatible_api()
    example_decorator_auto_inference()
    example_with_prefix()
    example_complex_action_server()
    example_multi_version_compatibility()

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
