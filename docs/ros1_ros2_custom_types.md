# ROS1 与 ROS2 自定义数据格式差异（msg/srv/action）

## 总览
- `msg/srv/action` 的文本定义思路在 ROS1/ROS2 中保持一致，但构建系统、代码生成链路、Python API 与通信语义有明显差异。
- 迁移时，定义文件本身通常改动小，工程配置与运行时行为改动更大。

## 1. 构建与代码生成
| 维度 | ROS1 | ROS2 |
|------|------|------|
| 构建系统 | `catkin` | `ament` + `colcon` |
| 接口生成 | `message_generation`/`message_runtime` | `rosidl_default_generators`/`rosidl_default_runtime` |
| 接口声明位置 | `CMakeLists.txt` + `package.xml` | `CMakeLists.txt` + `package.xml`（依赖名不同） |
| 语言后端 | gencpp/genpy 等 | rosidl 多语言后端 |

## 2. Python 导入与类型使用
| 维度 | ROS1 | ROS2 |
|------|------|------|
| 消息导入 | `from pkg.msg import MsgType` | `from pkg.msg import MsgType` |
| 服务导入 | `from pkg.srv import SrvType` | `from pkg.srv import SrvType` |
| 动作导入 | 常见 `pkg.msg` 下的 ActionGoal/Result/Feedback + `actionlib` | `from pkg.action import ActionType` + `rclpy.action` |
| 节点 API | `rospy.Publisher/Subscriber/ServiceProxy/Service` | `node.create_publisher/subscription/client/service` |

## 3. 服务与动作回调签名差异
- ROS1 服务回调常见：`handler(request) -> response`。
- ROS2 服务回调常见：`handler(request, response) -> response`。
- ROS1 动作主要通过 `actionlib`（`SimpleActionClient/Server`）工作。
- ROS2 动作使用 `rclpy.action.ActionClient/ActionServer`，并有更明确的 GoalHandle/Feedback/Result 流程。

## 4. 通信语义差异（会影响自定义接口行为）
- ROS1 以 TCPROS/UDPROS 为主；ROS2 基于 DDS。
- ROS2 引入 QoS（可靠性、历史深度、持久性等），同一 `msg` 在不同 QoS 下行为可不同。
- 因此“数据定义一致”不等于“通信行为一致”。

## 5. 迁移建议
- 优先保持 `.msg/.srv/.action` 字段定义稳定，先迁移构建系统与运行时 API。
- 明确 ROS2 QoS 策略，尤其是高频 Topic 与 latched 对应行为。
- 服务与动作的回调签名、返回对象构造需单独审查。
- 用包装层（如本项目）隔离 API 差异，把业务逻辑保持在统一接口之上。
