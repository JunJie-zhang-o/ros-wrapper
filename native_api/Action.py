#!/usr/bin/env python3
"""Native Action API comparison examples (ROS1 vs ROS2)."""

import time


# =========================
# Action server examples
# =========================
def server_ros1():
    import actionlib
    import rospy
    from actionlib_tutorials.msg import FibonacciAction, FibonacciFeedback, FibonacciResult

    def execute(goal):
        feedback = FibonacciFeedback()
        feedback.sequence = [0, 1]
        for _ in range(2, goal.order):
            if server.is_preempt_requested():
                server.set_preempted()
                return
            feedback.sequence.append(feedback.sequence[-1] + feedback.sequence[-2])
            server.publish_feedback(feedback)
            rospy.sleep(0.2)
        result = FibonacciResult()
        result.sequence = feedback.sequence
        server.set_succeeded(result)

    rospy.init_node("ros1_fibonacci_server")
    server = actionlib.SimpleActionServer("/fibonacci", FibonacciAction, execute, False)
    server.start()
    rospy.spin()


def server_ros2_inherit():
    import rclpy
    from action_tutorials_interfaces.action import Fibonacci
    from rclpy.action import ActionServer
    from rclpy.node import Node

    class Server(Node):
        def __init__(self):
            super().__init__("ros2_fibonacci_server")
            self.server = ActionServer(self, Fibonacci, "/fibonacci", self.execute_callback)

        def execute_callback(self, goal_handle):
            feedback = Fibonacci.Feedback()
            feedback.partial_sequence = [0, 1]
            for _ in range(2, goal_handle.request.order):
                feedback.partial_sequence.append(
                    feedback.partial_sequence[-1] + feedback.partial_sequence[-2]
                )
                goal_handle.publish_feedback(feedback)
                time.sleep(0.2)
            goal_handle.succeed()
            result = Fibonacci.Result()
            result.sequence = feedback.partial_sequence
            return result

    rclpy.init()
    node = Server()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


def server_ros2_non_inherit():
    import rclpy
    from action_tutorials_interfaces.action import Fibonacci
    from rclpy.action import ActionServer

    rclpy.init()
    node = rclpy.create_node("ros2_fibonacci_server_non_inherit")

    def execute_callback(goal_handle):
        feedback = Fibonacci.Feedback()
        feedback.partial_sequence = [0, 1]
        for _ in range(2, goal_handle.request.order):
            feedback.partial_sequence.append(
                feedback.partial_sequence[-1] + feedback.partial_sequence[-2]
            )
            goal_handle.publish_feedback(feedback)
            time.sleep(0.2)
        goal_handle.succeed()
        result = Fibonacci.Result()
        result.sequence = feedback.partial_sequence
        return result

    action_server = ActionServer(node, Fibonacci, "/fibonacci", execute_callback)
    rclpy.spin(node)
    action_server.destroy()
    node.destroy_node()
    rclpy.shutdown()


# =========================
# Action client examples
# =========================
def client_ros1():
    import actionlib
    import rospy
    from actionlib_tutorials.msg import FibonacciAction, FibonacciGoal

    rospy.init_node("ros1_fibonacci_client")
    client = actionlib.SimpleActionClient("/fibonacci", FibonacciAction)
    client.wait_for_server()
    goal = FibonacciGoal(order=8)
    client.send_goal(goal)
    client.wait_for_result()
    result = client.get_result()
    rospy.loginfo("ros1 action result: %s", result.sequence)


def client_ros2_inherit():
    import rclpy
    from action_tutorials_interfaces.action import Fibonacci
    from rclpy.action import ActionClient
    from rclpy.node import Node

    class Client(Node):
        def __init__(self):
            super().__init__("ros2_fibonacci_client")
            self.client = ActionClient(self, Fibonacci, "/fibonacci")

        def run(self):
            self.client.wait_for_server()
            goal = Fibonacci.Goal()
            goal.order = 8
            send_future = self.client.send_goal_async(goal)
            rclpy.spin_until_future_complete(self, send_future)
            goal_handle = send_future.result()
            result_future = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, result_future)
            result = result_future.result().result
            self.get_logger().info(f"ros2 action result: {result.sequence}")

    rclpy.init()
    node = Client()
    node.run()
    node.destroy_node()
    rclpy.shutdown()


def client_ros2_non_inherit():
    import rclpy
    from action_tutorials_interfaces.action import Fibonacci
    from rclpy.action import ActionClient

    rclpy.init()
    node = rclpy.create_node("ros2_fibonacci_client_non_inherit")
    client = ActionClient(node, Fibonacci, "/fibonacci")

    client.wait_for_server()
    goal = Fibonacci.Goal()
    goal.order = 8

    send_future = client.send_goal_async(goal)
    rclpy.spin_until_future_complete(node, send_future)
    goal_handle = send_future.result()

    result_future = goal_handle.get_result_async()
    rclpy.spin_until_future_complete(node, result_future)
    result = result_future.result().result
    node.get_logger().info(f"ros2 non-inherit action result: {result.sequence}")

    node.destroy_node()
    rclpy.shutdown()
