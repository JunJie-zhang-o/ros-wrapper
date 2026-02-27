#!/usr/bin/env python3
"""Native Service API comparison examples (ROS1 vs ROS2)."""


# =========================
# Service server examples
# =========================
def server_ros1():
    import rospy
    from std_srvs.srv import SetBool, SetBoolResponse

    def handle(req):
        status = "enabled" if req.data else "disabled"
        return SetBoolResponse(success=True, message=f"state: {status}")

    rospy.init_node("ros1_set_bool_server")
    rospy.Service("/set_enabled", SetBool, handle)
    rospy.spin()


def server_ros2_inherit():
    import rclpy
    from rclpy.node import Node
    from std_srvs.srv import SetBool

    class Server(Node):
        def __init__(self):
            super().__init__("ros2_set_bool_server")
            self.srv = self.create_service(SetBool, "/set_enabled", self.handle)

        def handle(self, req, resp):
            status = "enabled" if req.data else "disabled"
            resp.success = True
            resp.message = f"state: {status}"
            return resp

    rclpy.init()
    node = Server()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


def server_ros2_non_inherit():
    import rclpy
    from std_srvs.srv import SetBool

    rclpy.init()
    node = rclpy.create_node("ros2_set_bool_server_non_inherit")

    def handle(req, resp):
        status = "enabled" if req.data else "disabled"
        resp.success = True
        resp.message = f"state: {status}"
        return resp

    _srv = node.create_service(SetBool, "/set_enabled", handle)
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


# =========================
# Service client examples
# =========================
def client_ros1():
    import rospy
    from std_srvs.srv import SetBool

    rospy.init_node("ros1_set_bool_client")
    rospy.wait_for_service("/set_enabled")
    client = rospy.ServiceProxy("/set_enabled", SetBool)
    resp = client(True)
    rospy.loginfo("ros1 response: success=%s message=%s", resp.success, resp.message)


def client_ros2_inherit():
    import rclpy
    from rclpy.node import Node
    from std_srvs.srv import SetBool

    class Client(Node):
        def __init__(self):
            super().__init__("ros2_set_bool_client")
            self.client = self.create_client(SetBool, "/set_enabled")

        def run(self):
            while not self.client.wait_for_service(timeout_sec=1.0):
                pass
            req = SetBool.Request()
            req.data = True
            future = self.client.call_async(req)
            rclpy.spin_until_future_complete(self, future)
            resp = future.result()
            self.get_logger().info(
                f"ros2 response: success={resp.success} message={resp.message}"
            )

    rclpy.init()
    node = Client()
    node.run()
    node.destroy_node()
    rclpy.shutdown()


def client_ros2_non_inherit():
    import rclpy
    from std_srvs.srv import SetBool

    rclpy.init()
    node = rclpy.create_node("ros2_set_bool_client_non_inherit")
    client = node.create_client(SetBool, "/set_enabled")
    while not client.wait_for_service(timeout_sec=1.0):
        pass
    req = SetBool.Request()
    req.data = True
    future = client.call_async(req)
    rclpy.spin_until_future_complete(node, future)
    resp = future.result()
    node.get_logger().info(f"ros2 non-inherit response: {resp.success} {resp.message}")
    node.destroy_node()
    rclpy.shutdown()
