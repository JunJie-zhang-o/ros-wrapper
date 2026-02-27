# Findings & Decisions

## Requirements
- 使用 Python 实现一个轻量 ROS 包装器，隔离 ROS1 与 ROS2 二次开发差异。
- 启动时根据配置创建 ROS 实例：`ROS1` 或 `ROS2`。
- 模式1：通过抽象实例方法直接返回发布者、订阅者、服务客户端/服务器、动作客户端/服务器。
- 模式2：通过装饰器向函数注入原始 ROS 实体，并给函数添加 `ros_meta` 元信息。
- 装饰器形式要求：`类实例.function`，包括 `Publish`、`Subscribe`、`Service`、`Action`。
- `Service` 与 `Action` 根据被包装函数参数（`client`/`server`）决定注入客户端或服务端对象。
- 需要说明 ROS1/ROS2 在自定义数据格式（msg/srv/action）上的差别。
- 项目使用 `pdm` 管理，版本信息动态从库中读取。
- 项目结构不使用 `src` 布局，根目录直接放项目包目录。

## Research Findings
- 该仓库当前为空仓库，可从零设计 API。
- 需要通过延迟导入隔离 `rospy` 与 `rclpy` 环境依赖，避免无 ROS 环境时导入即失败。
- 装饰器元信息可统一为 dataclass/dict schema，便于后续静态扫描。
- `Service` / `Action` 通过函数签名自动识别 `client` 或 `server` 可实现低侵入式注入。
- ROS2 服务端默认回调签名与 ROS1 不同，包装层需要提供分后端的默认处理函数。

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 设计统一 `RosWrapper` 门面 + `RosBackend` 协议 | 清晰分层，便于 ROS1/ROS2 适配 |
| 将模式2装饰器做成实例方法（`wrapper.Publish(...)`） | 满足用户指定的调用形式 |
| 注入采用关键字参数（默认键：`publisher/subscriber/client/server`） | 显式可读，避免位置参数歧义 |
| `ros_meta` 用结构化对象列表挂在函数上 | 支持后续静态获取装饰器信息 |
| 用 `RosWrapper.from_version(...)` 快速创建实例 | 简化按配置启动 ROS1/ROS2 |
| 通过 `docs/ros1_ros2_custom_types.md` 单独沉淀差异说明 | 让数据格式迁移知识可独立复用 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `python` 不存在 | 全部命令改为 `python3` |
| 环境未安装 `pytest` | 使用 `python3` 内联断言脚本做最小行为验证 |

## Resources
- `/Users/jay/SpaceForPersonal/06-ros-wrapper/.codex/skills/planning-with-files/SKILL.md`
- `/Users/jay/SpaceForPersonal/06-ros-wrapper/README.md`
- `/Users/jay/SpaceForPersonal/06-ros-wrapper/docs/ros1_ros2_custom_types.md`

## Visual/Browser Findings
- 无。

## 2026-02-28 Interface Refactor Findings
- Backend abstraction renamed from `create_*` to direct methods: `publisher/subscriber/service_client/service_server/action_client/action_server`.
- Wrapper now exposes three API groups in one facade: custom unified APIs, ROS1-compatible APIs, ROS2-compatible APIs.
- Added `Topic` decorator for publisher/subscriber role inference from function signature.
- Metadata write-path changed: only `__ros_meta__` is written; `get_ros_meta()` now reads from `__ros_meta__`.
