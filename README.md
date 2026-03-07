# ros-wrapper

一个轻量型 Python ROS 包装器，用于隔离 ROS1 与 ROS2 二次开发差异。

## 目标
- 通过配置创建 ROS1 或 ROS2 运行实例。
- wrapper 同时提供三类接口：
  - 自定义统一接口
  - ROS1 兼容接口
  - ROS2 兼容接口
- 提供装饰器模式：`Topic` / `Service` / `Action`（`Publish` / `Subscribe` 作为语义别名）。

## 破坏性变更
`ROSBackend` 已移除旧的 `create_*` 方法，仅保留以下 6 个方法：
- `publisher`
- `subscriber`
- `service_client`
- `service_server`
- `action_client`
- `action_server`

## 安装与开发
```bash
pdm install
pdm run check
```

## CI / 发布
- GitHub Actions 会在 push / pull request 到 `main` 时运行 `compileall` 与 `pytest`（Python 3.10/3.11/3.12）。
- 推送任意 tag（如 `v0.1.0`）会先完成上述检查，再执行 `python -m build` 并使用仓库机密 `PYPI_API_TOKEN` 自动发布到 PyPI。

## 三类接口

### 1) 自定义统一接口
```python
wrapper.publisher(topic, msg_type, **kwargs)
wrapper.subscriber(topic, msg_type, callback=..., **kwargs)
wrapper.service_client(name, srv_type, **kwargs)
wrapper.service_server(name, srv_type, handler=..., **kwargs)
wrapper.action_client(name, action_type, **kwargs)
wrapper.action_server(name, action_type, execute_callback=..., **kwargs)
wrapper.init()
wrapper.spin()
wrapper.shutdown()
```

### 2) ROS1 兼容接口
```python
wrapper.Publisher(topic, msg_type, **kwargs)
wrapper.Subscriber(topic, msg_type, callback=..., **kwargs)
wrapper.Service(name, srv_type, handler, **kwargs)
wrapper.ServiceProxy(name, srv_type, **kwargs)
wrapper.SimpleActionClient(name, action_type, **kwargs)
wrapper.SimpleActionServer(name, action_type, execute_cb=..., **kwargs)
```

### 3) ROS2 兼容接口
```python
wrapper.create_publisher(msg_type, topic, qos_profile=10, **kwargs)
wrapper.create_subscription(msg_type, topic, callback, qos_profile=10, **kwargs)
wrapper.create_client(srv_type, name, **kwargs)
wrapper.create_service(srv_type, name, callback=..., **kwargs)
wrapper.ActionClient(action_type, name, **kwargs)
wrapper.ActionServer(action_type, name, execute_callback=..., **kwargs)
```

## 装饰器
- `Topic`：根据被装饰函数参数自动推断注入 `publisher` 或 `subscriber`。
- `Service`：根据函数参数中的 `client` / `server` 自动注入。
- `Action`：根据函数参数中的 `client` / `server` 自动注入。
- `Publish` / `Subscribe`：分别固定注入发布者/订阅者。

示例：
```python
from ros_wrapper import ROSVersion, ROSWrapper, get_ros_meta

wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="demo")

@wrapper.Topic("/chatter", String)
def send(*, publisher):
    publisher.publish(String(data="hello"))

@wrapper.Service("/calc", AddTwoInts)
def call(*, client):
    return client(1, 2)

print(get_ros_meta(send))
```

## Prefix 参数
- 可通过 `ROSConfig(prefix=...)` 或 `ROSWrapper.from_version(..., prefix=...)` 设置统一前缀。
- 前缀会自动加到所有 `topic/service/action` 名称前面（自定义接口、ROS1兼容接口、ROS2兼容接口、装饰器注入都生效）。
- 已带相同前缀的名称不会重复添加。

示例：
```python
from ros_wrapper import ROSVersion, ROSWrapper

wrapper = ROSWrapper.from_version(ROSVersion.ROS2, node_name="demo", prefix="/module_a")
pub = wrapper.publisher("/chatter", String)          # 实际使用: /module_a/chatter
client = wrapper.service_client("/calc", AddTwoInts) # 实际使用: /module_a/calc
```

## 元信息约定
装饰器元信息只写入 `__ros_meta__`，并以 tuple 追加保留历史。

推荐统一通过 `get_ros_meta(target)` 读取，也可直接访问 `target.__ros_meta__`。

## ROS2 auto_init 规则
- 当 `version=ROSVersion.ROS2` 时，`ROSConfig` 会强制 `auto_init=True`。
- 当 `version=ROSVersion.ROS1` 时，`auto_init` 保持用户传入值。
- `wrapper.init()` 可手动调用，作为统一入口屏蔽 ROS1/ROS2 初始化差异（重复调用是安全的）。

## 动态版本
版本号定义在 `ros_wrapper/__init__.py` 的 `__version__`，`pdm` 通过 `tool.pdm.version.source = "file"` 动态读取。

## ROS1/ROS2 自定义数据格式差异
见文档：`docs/ros1_ros2_custom_types.md`。
