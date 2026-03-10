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

## 2026-03-10 ServiceClient Compatibility Findings
- Current unified wrapper already normalized factory return types, but `ServiceClient` only exposed `call`, missing explicit `call_async`.
- Added cross-version `call_async` contract:
  - ROS2: direct passthrough to native `call_async`.
  - ROS1: wraps sync native call in a background thread and returns `concurrent.futures.Future`.
- Refactored `call` to always consume `call_async` path, so user code can rely on both entry points in ROS1/ROS2.
- Added `ros_wrapper/clients.pyi` to expose wrapper class methods and callback contracts for IDE completion and static analysis.

## 2026-03-10 Remaining Client Interface Completion
- Added `ActionClient.call` / `ActionClient.call_async` unified aliases:
  - `call` maps to synchronous `send_goal_and_wait`.
  - `call_async` maps to asynchronous `send_goal` and returns `ActionGoalHandle`.
- Added `ActionClient.send_goal_async` alias for ROS2-style naming while keeping ROS1 compatibility.
- Improved ROS2 fallback behavior for environments without `rclpy` import:
  - only import `rclpy` when a node is provided and spinning is required;
  - use lightweight polling fallback for node-less test/mock scenarios.

## 2026-03-11 Repository Deep Review Findings
- Architecture is generally clean: facade + backend adapter + unified clients wrapper has clear layering.
- Confirmed two ROS1 runtime defects by direct local reproduction:
  - Default ROS1 service handler signature mismatch: default handler is one-arg, but ROS1 wrapper adapter always invokes `(request, response)`.
  - `ActionGoalHandle.get_result` ROS1 path depends on private attribute `_rospy` on native client; this is not part of SimpleActionClient public contract.
- Test coverage gap:
  - Existing tests rely on permissive mocks and do not exercise real-shape ROS1 client/server objects for the two paths above.

## 2026-03-11 ROS1 Runtime Bugfix Decisions
- `_wrap_service_handler_for_ros1` now supports both callback signatures:
  - ROS1 style: `handler(request)`
  - Unified style: `handler(request, response)`
- Signature routing is done once via `inspect.signature`, avoiding broad `TypeError` swallow behavior.
- `ActionGoalHandle.get_result` ROS1 timeout handling now uses public `rospy.Duration(timeout)` instead of private native attribute access.
- Added regression tests:
  - `test_ros1_handler_wrapping_supports_single_arg_handler`
  - `test_goal_handle_get_result_timeout_uses_rospy_duration`
