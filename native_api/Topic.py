#!/usr/bin/env python3
"""Native Topic API comparison examples (ROS1 vs ROS2)."""


# =========================
# Publisher examples
# =========================
def publisher_ros1():
    import rospy
    from std_msgs.msg import String

    rospy.init_node("ros1_talker")
    pub = rospy.Publisher("/chatter", String, queue_size=10)
    rate = rospy.Rate(1)
    i = 0
    while not rospy.is_shutdown():
        pub.publish(f"hello ros1 {i}")
        i += 1
        rate.sleep()


def publisher_ros2_inherit():
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    class Talker(Node):
        def __init__(self):
            super().__init__("ros2_talker")
            self.pub = self.create_publisher(String, "/chatter", 10)
            self.i = 0
            self.timer = self.create_timer(1.0, self.tick)

        def tick(self):
            msg = String()
            msg.data = f"hello ros2 {self.i}"
            self.pub.publish(msg)
            self.i += 1

    rclpy.init()
    node = Talker()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


def publisher_ros2_non_inherit():
    import rclpy
    from std_msgs.msg import String

    rclpy.init()
    node = rclpy.create_node("ros2_talker_non_inherit")
    pub = node.create_publisher(String, "/chatter", 10)
    state = {"i": 0}

    def tick():
        msg = String()
        msg.data = f"hello ros2 non-inherit {state['i']}"
        pub.publish(msg)
        state["i"] += 1

    timer = node.create_timer(1.0, tick)
    rclpy.spin(node)
    timer.cancel()
    node.destroy_node()
    rclpy.shutdown()


# =========================
# Subscriber examples
# =========================
def subscriber_ros1():
    import rospy
    from std_msgs.msg import String

    def callback(msg):
        rospy.loginfo("ros1 recv: %s", msg.data)

    rospy.init_node("ros1_listener")
    rospy.Subscriber("/chatter", String, callback)
    rospy.spin()


def subscriber_ros2_inherit():
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    class Listener(Node):
        def __init__(self):
            super().__init__("ros2_listener")
            self.sub = self.create_subscription(String, "/chatter", self.callback, 10)

        def callback(self, msg):
            self.get_logger().info(f"ros2 recv: {msg.data}")

    rclpy.init()
    node = Listener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


def subscriber_ros2_non_inherit():
    import rclpy
    from std_msgs.msg import String

    rclpy.init()
    node = rclpy.create_node("ros2_listener_non_inherit")

    def callback(msg):
        node.get_logger().info(f"ros2 non-inherit recv: {msg.data}")

    _sub = node.create_subscription(String, "/chatter", callback, 10)
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
