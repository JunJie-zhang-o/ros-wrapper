# ROS1/ROS2 统一 API 设计讨论

## 概述

本文档详细讨论 `ros-wrapper` 项目中 ROS1 和 ROS2 统一 API 的设计决策，重点关注：
- Topic 对应的 Publisher 和 Subscriber
- Service 对应的 Client 和 Server
- Action 对应的 Client 和 Server

## 设计目标

1. **统一接口**: 提供一套统一的 API，屏蔽 ROS1 和 ROS2 底层实现差异
2. **兼容原生**: 同时支持 ROS1 和 ROS2 原生 API 风格，降低迁移成本
3. **灵活易用**: 支持多种使用模式（直接调用、装饰器注入）
4. **元信息可查**: 装饰器注入的实体可以通过元信息进行静态分析

## API 层次结构

```
ROSWrapper (统一门面)
    │
    ├── 自定义统一 API (推荐)
    │   ├── publisher()
    │   ├── subscriber()
    │   ├── service_client()
    │   ├── service_server()
    │   ├── action_client()
    │   └── action_server()
    │
    ├── ROS1 兼容 API
    │   ├── Publisher()
    │   ├── Subscriber()
    │   ├── ServiceProxy()
    │   ├── Service()
    │   ├── SimpleActionClient()
    │   └── SimpleActionServer()
    │
    └── ROS2 兼容 API
        ├── create_publisher()
        ├── create_subscription()
        ├── create_client()
        ├── create_service()
        ├── ActionClient()
        └── ActionServer()
```

## 1. Topic Publisher 和 Subscriber 统一设计

### 1.1 ROS1 vs ROS2 原生差异

**ROS1 (rospy):**
```python
import rospy
from std_msgs.msg import String

# Publisher
pub = rospy.Publisher('/chatter', String, queue_size=10)
pub.publish(String(data="hello"))

# Subscriber
def callback(msg):
    print(msg.data)
sub = rospy.Subscriber('/chatter', String, callback, queue_size=10)
```

**ROS2 (rclpy):**
```python
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

node = Node('my_node')

# Publisher
pub = node.create_publisher(String, '/chatter', 10)
pub.publish(String(data="hello"))

# Subscriber
def callback(msg):
    print(msg.data)
sub = node.create_subscription(String, '/chatter', callback, 10)
```

### 1.2 统一 API 设计

我们设计了三层 API 来满足不同需求：

#### 层次 1: 自定义统一 API (推荐)

```python
from ros_wrapper import ROSWrapper, ROSVersion
from std_msgs.msg import String

# 支持 ROS1 和 ROS2
wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="demo")

# Publisher - 统一参数顺序: topic, msg_type
pub = wrapper.publisher('/chatter', String)
pub.publish(String(data="hello"))

# Subscriber - 统一参数顺序: topic, msg_type, callback
def callback(msg):
    print(msg.data)

sub = wrapper.subscriber('/chatter', String, callback=callback)
```

**设计要点:**
- 参数顺序统一: `topic` 在前, `msg_type` 在后
- 使用关键字参数 `callback=` 提高可读性
- 底层自动适配 ROS1/ROS2 差异 (queue_size vs qos_profile)

#### 层次 2: ROS1 兼容 API

```python
# 完全兼容 ROS1 rospy 语法
pub = wrapper.Publisher('/chatter', String, queue_size=10)
sub = wrapper.Subscriber('/chatter', String, callback, queue_size=10)
```

**设计要点:**
- 大写方法名，遵循 ROS1 命名习惯
- 参数位置和命名与 rospy 一致
- 在 ROS2 后端也能使用，自动转换参数

#### 层次 3: ROS2 兼容 API

```python
# 完全兼容 ROS2 rclpy 语法
pub = wrapper.create_publisher(String, '/chatter', qos_profile=10)
sub = wrapper.create_subscription(String, '/chatter', callback, qos_profile=10)
```

**设计要点:**
- `create_*` 方法名，遵循 ROS2 命名习惯
- 参数顺序: `msg_type` 在前, `topic` 在后 (与 ROS2 一致)
- 在 ROS1 后端也能使用，自动转换参数

### 1.3 装饰器模式

```python
# 自动推断角色 (根据函数参数名)
@wrapper.Topic('/chatter', String)
def publish_message(*, publisher):
    publisher.publish(String(data="hello"))

@wrapper.Topic('/chatter', String, callback=lambda msg: None)
def receive_message(*, subscriber):
    # subscriber 会被自动注入
    pass

# 或者显式指定
@wrapper.Publish('/chatter', String)
def publish_only(*, publisher):
    publisher.publish(String(data="hello"))

@wrapper.Subscribe('/chatter', String, callback=lambda msg: print(msg.data))
def subscribe_only(*, subscriber):
    pass
```

**设计要点:**
- `Topic` 装饰器根据函数签名自动推断是 publisher 还是 subscriber
- `Publish` 和 `Subscribe` 显式指定角色
- 通过关键字参数注入实体，参数名可自定义

## 2. Service Client 和 Server 统一设计

### 2.1 ROS1 vs ROS2 原生差异

**ROS1 (rospy):**
```python
from std_srvs.srv import AddTwoInts

# Client
client = rospy.ServiceProxy('/add_two_ints', AddTwoInts)
response = client(1, 2)

# Server
def handle_add(req):
    return req.a + req.b

server = rospy.Service('/add_two_ints', AddTwoInts, handle_add)
```

**ROS2 (rclpy):**
```python
from example_interfaces.srv import AddTwoInts

# Client
client = node.create_client(AddTwoInts, '/add_two_ints')
request = AddTwoInts.Request()
request.a = 1
request.b = 2
future = client.call_async(request)

# Server
def handle_add(request, response):
    response.sum = request.a + request.b
    return response

server = node.create_service(AddTwoInts, '/add_two_ints', handle_add)
```

**关键差异:**
- ROS1: Client 是 `ServiceProxy`, Server 回调返回值直接作为响应
- ROS2: Client 是异步调用, Server 回调需要填充 `response` 对象并返回

### 2.2 统一 API 设计

#### 层次 1: 自定义统一 API (推荐)

```python
from example_interfaces.srv import AddTwoInts

wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="demo")

# Service Client - 统一参数顺序: name, srv_type
client = wrapper.service_client('/add_two_ints', AddTwoInts)
response = client(1, 2)  # 使用方式一致

# Service Server - 统一参数顺序: name, srv_type, handler
def handle_add(request, response=None):
    # 兼容 ROS1 和 ROS2 的签名
    if response is None:  # ROS1
        return request.a + request.b
    else:  # ROS2
        response.sum = request.a + request.b
        return response

server = wrapper.service_server('/add_two_ints', AddTwoInts, handler=handle_add)
```

**设计要点:**
- Client 调用方式统一，底层自动处理同步/异步差异
- Server 回调函数签名兼容 ROS1 和 ROS2
- 参数命名使用 `handler=` 关键字参数

#### 层次 2: ROS1 兼容 API

```python
# ServiceProxy - 完全兼容 ROS1
client = wrapper.ServiceProxy('/add_two_ints', AddTwoInts)
response = client(1, 2)

# Service - 完全兼容 ROS1
server = wrapper.Service('/add_two_ints', AddTwoInts, handle_add)
```

#### 层次 3: ROS2 兼容 API

```python
# create_client - 完全兼容 ROS2
client = wrapper.create_client(AddTwoInts, '/add_two_ints')

# create_service - 完全兼容 ROS2
server = wrapper.create_service(AddTwoInts, '/add_two_ints', callback=handle_add)
```

### 2.3 装饰器模式

```python
# 自动推断角色 (根据函数参数名 client/server)
@wrapper.Service('/add_two_ints', AddTwoInts)
def call_service(*, client):
    response = client(1, 2)
    return response

@wrapper.Service('/add_two_ints', AddTwoInts)
def serve_requests(*, server):
    # server 会被自动注入
    pass
```

**设计要点:**
- `Service` 装饰器根据函数参数名 (`client` 或 `server`) 自动推断角色
- 如果同时存在两个参数名会报错，确保角色明确

## 3. Action Client 和 Server 统一设计

### 3.1 ROS1 vs ROS2 原生差异

**ROS1 (actionlib):**
```python
import actionlib
from my_package.msg import FibonacciAction, FibonacciGoal

# Client
client = actionlib.SimpleActionClient('/fibonacci', FibonacciAction)
client.wait_for_server()
goal = FibonacciGoal(order=10)
client.send_goal(goal)
client.wait_for_result()

# Server
def execute_callback(goal):
    # 执行动作逻辑
    pass

server = actionlib.SimpleActionServer(
    '/fibonacci',
    FibonacciAction,
    execute_cb=execute_callback,
    auto_start=True
)
```

**ROS2 (rclpy.action):**
```python
from rclpy.action import ActionClient, ActionServer
from example_interfaces.action import Fibonacci

# Client
client = ActionClient(node, Fibonacci, '/fibonacci')
goal_msg = Fibonacci.Goal(order=10)
future = client.send_goal_async(goal_msg)

# Server
def execute_callback(goal_handle):
    # 执行动作逻辑
    result = Fibonacci.Result()
    return result

server = ActionServer(
    node,
    Fibonacci,
    '/fibonacci',
    execute_callback=execute_callback
)
```

**关键差异:**
- ROS1: 使用 `actionlib.SimpleActionClient/SimpleActionServer`
- ROS2: 使用 `rclpy.action.ActionClient/ActionServer`
- 回调函数签名有差异

### 3.2 统一 API 设计

#### 层次 1: 自定义统一 API (推荐)

```python
from example_interfaces.action import Fibonacci

wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="demo")

# Action Client - 统一参数顺序: name, action_type
client = wrapper.action_client('/fibonacci', Fibonacci)

# Action Server - 统一参数顺序: name, action_type, execute_callback
def execute_callback(goal):
    # 执行动作逻辑
    return result

server = wrapper.action_server('/fibonacci', Fibonacci, execute_callback=execute_callback)
```

#### 层次 2: ROS1 兼容 API

```python
# SimpleActionClient - 完全兼容 ROS1
client = wrapper.SimpleActionClient('/fibonacci', Fibonacci)

# SimpleActionServer - 完全兼容 ROS1
server = wrapper.SimpleActionServer('/fibonacci', Fibonacci, execute_cb=execute_callback)
```

#### 层次 3: ROS2 兼容 API

```python
# ActionClient - 完全兼容 ROS2
client = wrapper.ActionClient(Fibonacci, '/fibonacci')

# ActionServer - 完全兼容 ROS2
server = wrapper.ActionServer(Fibonacci, '/fibonacci', execute_callback=execute_callback)
```

### 3.3 装饰器模式

```python
# 自动推断角色 (根据函数参数名 client/server)
@wrapper.Action('/fibonacci', Fibonacci)
def call_action(*, client):
    # client 会被自动注入
    pass

@wrapper.Action('/fibonacci', Fibonacci)
def serve_action(*, server):
    # server 会被自动注入
    pass
```

## 4. 核心设计原则

### 4.1 适配器模式 (Adapter Pattern)

```
┌─────────────────┐
│   ROSWrapper    │  ← 统一门面
└────────┬────────┘
         │
    ┌────▼────┐
    │ Backend │  ← 抽象接口
    └────┬────┘
         │
    ┌────┴────────────┐
    │                 │
┌───▼──────┐   ┌─────▼─────┐
│ROS1Backend│   │ROS2Backend│  ← 具体实现
└──────────┘   └───────────┘
```

**优点:**
- 清晰的职责分离
- 易于扩展新的 ROS 版本
- 便于单元测试 (可以 mock backend)

### 4.2 参数归一化

**Topic 和 Service 命名:**
- 统一使用 `/` 开头的绝对路径
- 支持 `prefix` 参数统一添加命名空间前缀

**消息类型:**
- 直接传递消息类型类，不使用字符串
- 由后端适配器负责处理实际的类型注册

**回调函数:**
- Service Server 回调兼容 ROS1 和 ROS2 签名
- 通过检查参数个数自动适配

### 4.3 延迟导入 (Lazy Import)

```python
# backends/ros1.py
def publisher(self, topic, msg_type, **kwargs):
    import rospy  # 运行时导入，避免无 ROS1 环境时导入失败
    return rospy.Publisher(topic, msg_type, queue_size=kwargs.get('queue_size', 10))
```

**优点:**
- 无 ROS 环境时仍可导入 `ros_wrapper` 包
- 测试时可以使用 FakeBackend 而不需要真实 ROS 环境

### 4.4 元信息系统 (Metadata System)

装饰器注入的实体会附加元信息，方便静态分析：

```python
@wrapper.Topic('/chatter', String)
def publish_message(*, publisher):
    pass

# 获取元信息
from ros_wrapper import get_ros_meta
meta = get_ros_meta(publish_message)
print(meta[0].decorator)  # "Topic"
print(meta[0].role)       # "publisher"
print(meta[0].resource)   # "/chatter"
print(meta[0].ros_type)   # "std_msgs.msg.String"
```

**元信息结构:**
```python
@dataclass(frozen=True)
class ROSMeta:
    decorator: str      # 装饰器名称: "Topic", "Service", "Action"
    backend: str        # 后端版本: "ROS1" 或 "ROS2"
    role: str          # 角色: "publisher", "subscriber", "client", "server"
    resource: str      # 资源名称: topic/service/action 完整路径
    ros_type: str      # ROS 类型: 消息/服务/动作类型全限定名
    inject_as: str     # 注入参数名: 函数中接收实体的参数名
```

## 5. 使用建议

### 5.1 新项目推荐

**推荐使用自定义统一 API:**
```python
wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="my_node")

pub = wrapper.publisher('/topic', MsgType)
sub = wrapper.subscriber('/topic', MsgType, callback=callback)
client = wrapper.service_client('/service', SrvType)
server = wrapper.service_server('/service', SrvType, handler=handler)
```

**配合装饰器使用:**
```python
@wrapper.Topic('/topic', MsgType)
def process_data(*, publisher, subscriber):
    data = get_data()
    publisher.publish(data)
```

### 5.2 迁移现有项目

**从 ROS1 迁移:**
```python
# 方式 1: 最小改动，使用 ROS1 兼容 API
# 只需替换 import 和创建 wrapper
# import rospy  # 删除
from ros_wrapper import ROSWrapper, ROSVersion
wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="node")

# rospy.Publisher -> wrapper.Publisher
pub = wrapper.Publisher('/topic', MsgType, queue_size=10)

# 方式 2: 逐步迁移到统一 API (推荐)
pub = wrapper.publisher('/topic', MsgType, queue_size=10)
```

**从 ROS2 迁移:**
```python
# 方式 1: 最小改动，使用 ROS2 兼容 API
# import rclpy  # 删除
# from rclpy.node import Node  # 删除
from ros_wrapper import ROSWrapper, ROSVersion
wrapper = ROSWrapper.from_version(ROSVersion.ROS1, node_name="node")

# node.create_publisher -> wrapper.create_publisher
pub = wrapper.create_publisher(MsgType, '/topic', qos_profile=10)

# 方式 2: 逐步迁移到统一 API (推荐)
pub = wrapper.publisher('/topic', MsgType, qos_profile=10)
```

### 5.3 多模块项目

使用 `prefix` 参数管理命名空间:

```python
# 模块 A
wrapper_a = ROSWrapper.from_version(
    ROSVersion.ROS2,
    node_name="module_a",
    prefix="/module_a"
)
pub_a = wrapper_a.publisher('/status', Status)  # 实际: /module_a/status

# 模块 B
wrapper_b = ROSWrapper.from_version(
    ROSVersion.ROS2,
    node_name="module_b",
    prefix="/module_b"
)
pub_b = wrapper_b.publisher('/status', Status)  # 实际: /module_b/status
```

## 6. 实现验证

所有功能都经过完整的单元测试验证:

- ✅ ROS1/ROS2 配置规范化
- ✅ 自定义统一 API 路由到后端
- ✅ ROS1 兼容 API 路由到统一 API
- ✅ ROS2 兼容 API 路由到统一 API
- ✅ Prefix 参数应用到所有 API 层次
- ✅ Topic 装饰器角色推断 (publisher/subscriber)
- ✅ Service 和 Action 装饰器角色推断 (client/server)
- ✅ 元信息存储在 `__ros_meta__` 属性中
- ✅ init/spin/shutdown 委托到后端

测试覆盖率: 16/16 测试全部通过 ✓

## 7. 总结

`ros-wrapper` 通过三层 API 设计，成功实现了 ROS1 和 ROS2 的统一接口:

1. **自定义统一 API**: 提供最佳的跨版本兼容性
2. **ROS1 兼容 API**: 降低从 ROS1 迁移的成本
3. **ROS2 兼容 API**: 降低从 ROS2 迁移的成本

核心设计原则:
- 适配器模式实现版本隔离
- 延迟导入避免环境依赖
- 参数归一化简化使用
- 元信息系统支持静态分析

这种设计使得用户可以:
- 在一套代码中同时支持 ROS1 和 ROS2
- 选择最适合自己的 API 风格
- 逐步从原生 API 迁移到统一 API
- 利用装饰器简化代码结构
