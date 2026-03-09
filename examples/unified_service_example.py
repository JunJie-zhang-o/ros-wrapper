"""
统一 Service API 示例

演示如何使用 ros-wrapper 统一的 Service Client 和 Server API，
支持在 ROS1 和 ROS2 之间无缝切换。
"""

from typing import Any

from ros_wrapper import ROSVersion, ROSWrapper


# 模拟服务类型（实际使用时替换为真实的服务类型）
class AddTwoInts:
    """模拟 example_interfaces.srv.AddTwoInts"""

    class Request:
        def __init__(self, a: int = 0, b: int = 0) -> None:
            self.a = a
            self.b = b

    class Response:
        def __init__(self, sum: int = 0) -> None:
            self.sum = sum


def example_unified_api() -> None:
    """示例 1: 使用自定义统一 API (推荐)"""
    print("\n=== 示例 1: 自定义统一 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="unified_service_demo", auto_init=False
    )

    try:
        # 创建 Service Client - 统一的参数顺序
        client = wrapper.service_client("/add_two_ints", AddTwoInts)
        print(f"Created service client: {client}")

        # 创建 Service Server - 使用关键字参数 handler
        def handle_add(request: Any, response: Any = None) -> Any:
            """兼容 ROS1 和 ROS2 的回调签名"""
            if response is None:  # ROS1 风格
                return request.a + request.b
            else:  # ROS2 风格
                response.sum = request.a + request.b
                return response

        server = wrapper.service_server("/add_two_ints", AddTwoInts, handler=handle_add)
        print(f"Created service server: {server}")

        # 调用服务（需要真实 ROS 环境）
        # result = client(1, 2)
        # print(f"Service result: {result}")

    finally:
        wrapper.close()


def example_ros1_compatible_api() -> None:
    """示例 2: 使用 ROS1 兼容 API"""
    print("\n=== 示例 2: ROS1 兼容 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS1, node_name="ros1_service_demo", auto_init=False
    )

    try:
        # 完全兼容 rospy.ServiceProxy 语法
        client = wrapper.ServiceProxy("/add_two_ints", AddTwoInts)
        print(f"Created ROS1-style client: {client}")

        # 完全兼容 rospy.Service 语法
        def handle_add(request: Any) -> int:
            """ROS1 风格回调: 直接返回结果值"""
            return request.a + request.b

        # 注意: ROS1 的 Service 接受 3 个位置参数
        server = wrapper.Service("/add_two_ints", AddTwoInts, handle_add)
        print(f"Created ROS1-style server: {server}")

    finally:
        wrapper.close()


def example_ros2_compatible_api() -> None:
    """示例 3: 使用 ROS2 兼容 API"""
    print("\n=== 示例 3: ROS2 兼容 API ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="ros2_service_demo", auto_init=False
    )

    try:
        # 完全兼容 node.create_client 语法
        # 注意: srv_type 在前, name 在后 (ROS2 风格)
        client = wrapper.create_client(AddTwoInts, "/add_two_ints")
        print(f"Created ROS2-style client: {client}")

        # 完全兼容 node.create_service 语法
        def handle_add(request: Any, response: Any) -> Any:
            """ROS2 风格回调: 填充 response 并返回"""
            response.sum = request.a + request.b
            return response

        server = wrapper.create_service(
            AddTwoInts, "/add_two_ints", callback=handle_add
        )
        print(f"Created ROS2-style server: {server}")

    finally:
        wrapper.close()


def example_decorator_auto_inference() -> None:
    """示例 4: 使用装饰器自动推断角色"""
    print("\n=== 示例 4: 装饰器自动推断角色 ===")

    wrapper = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="service_decorator_demo", auto_init=False
    )

    # 根据函数参数名 'client' 自动推断为 Service Client
    @wrapper.Service("/calculate", AddTwoInts)
    def call_calculation(*, client) -> None:
        """函数参数包含 'client'，自动注入 Service Client"""
        print(f"Service client injected: {client}")
        # result = client(10, 20)
        # print(f"Result: {result}")

    # 根据函数参数名 'server' 自动推断为 Service Server
    @wrapper.Service("/calculate", AddTwoInts)
    def serve_calculation(*, server) -> None:
        """函数参数包含 'server'，自动注入 Service Server"""
        print(f"Service server injected: {server}")

    # 调用函数时自动创建 ROS 实体
    call_calculation()
    serve_calculation()

    # 查看元信息
    from ros_wrapper import get_ros_meta

    meta1 = get_ros_meta(call_calculation)[0]
    print(f"\ncall_calculation 元信息:")
    print(f"  - decorator: {meta1.decorator}")
    print(f"  - role: {meta1.role}")
    print(f"  - resource: {meta1.resource}")

    meta2 = get_ros_meta(serve_calculation)[0]
    print(f"\nserve_calculation 元信息:")
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
        node_name="prefixed_service_demo",
        prefix="/robot_a",
        auto_init=False,
    )

    try:
        # 实际使用的服务名称为 /robot_a/control/set_speed
        client = wrapper.service_client("/control/set_speed", AddTwoInts)
        print(f"Service client with prefix: {client}")

        # 装饰器也会自动应用前缀
        @wrapper.Service("/control/get_status", AddTwoInts)
        def get_status(*, client) -> None:
            print(f"Service client with prefix from decorator: {client}")

        get_status()

        # 检查元信息中的实际路径
        from ros_wrapper import get_ros_meta

        meta = get_ros_meta(get_status)[0]
        print(f"Actual resource path: {meta.resource}")  # /robot_a/control/get_status

    finally:
        wrapper.close()


def example_handler_compatibility() -> None:
    """示例 6: Service 回调函数兼容性"""
    print("\n=== 示例 6: Service 回调函数兼容性 ===")

    # ROS1 风格回调
    def ros1_style_handler(request: Any) -> int:
        """ROS1: 直接返回结果值"""
        return request.a + request.b

    # ROS2 风格回调
    def ros2_style_handler(request: Any, response: Any) -> Any:
        """ROS2: 填充 response 对象并返回"""
        response.sum = request.a + request.b
        return response

    # 兼容两种风格的回调
    def compatible_handler(request: Any, response: Any = None) -> Any:
        """通过检查 response 参数适配两种风格"""
        result = request.a + request.b
        if response is None:
            return result
        else:
            response.sum = result
            return response

    # 在 ROS1 环境使用
    wrapper1 = ROSWrapper.from_version(
        ROSVersion.ROS1, node_name="ros1_handler_demo", auto_init=False
    )
    server1 = wrapper1.service_server(
        "/add", AddTwoInts, handler=compatible_handler
    )
    print(f"ROS1 server with compatible handler: {server1}")
    wrapper1.close()

    # 在 ROS2 环境使用同一个回调函数
    wrapper2 = ROSWrapper.from_version(
        ROSVersion.ROS2, node_name="ros2_handler_demo", auto_init=False
    )
    server2 = wrapper2.service_server(
        "/add", AddTwoInts, handler=compatible_handler
    )
    print(f"ROS2 server with compatible handler: {server2}")
    wrapper2.close()


def example_multi_version_compatibility() -> None:
    """示例 7: 同一代码支持多版本"""
    print("\n=== 示例 7: 同一代码支持多版本 ===")

    def create_service_node(ros_version: ROSVersion) -> None:
        """同一函数可以支持不同 ROS 版本"""
        wrapper = ROSWrapper.from_version(
            ros_version,
            node_name=f"service_multi_version_{ros_version.value}",
            auto_init=False,
        )

        try:
            # 使用统一 API，不需要关心底层版本
            client = wrapper.service_client("/compute", AddTwoInts)

            def handler(request: Any, response: Any = None) -> Any:
                result = request.a + request.b
                if response is None:
                    return result
                response.sum = result
                return response

            server = wrapper.service_server("/compute", AddTwoInts, handler=handler)

            print(f"\n{ros_version.value} 环境:")
            print(f"  Client: {client}")
            print(f"  Server: {server}")

        finally:
            wrapper.close()

    # 同一代码可以运行在不同版本
    create_service_node(ROSVersion.ROS1)
    create_service_node(ROSVersion.ROS2)


def main() -> None:
    """运行所有示例"""
    print("=" * 60)
    print("ROS Wrapper - 统一 Service API 示例")
    print("=" * 60)

    example_unified_api()
    example_ros1_compatible_api()
    example_ros2_compatible_api()
    example_decorator_auto_inference()
    example_with_prefix()
    example_handler_compatibility()
    example_multi_version_compatibility()

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
