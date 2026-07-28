# 通讯工程师交接说明：单设备通讯端

## 1. 交接范围

这部分代码交给通讯工程师负责，目标是完成“单台设备或单台工控机”的数据采集、缓存、上传和指令执行。

通讯工程师负责：

- C++ 上位机读取真实设备数据。
- 将实时数据写入 Windows 共享内存。
- 设备端上传服务读取共享内存。
- 本地缓存或本地数据库落库。
- 网络恢复后补传数据。
- 向总控平台上传实时快照。
- 从总控平台接收待执行指令。
- 将总控业务指令转成设备实际通讯指令。
- 回传指令执行结果。

通讯工程师不负责：

- 多设备总控平台页面。
- 用户权限。
- 报表页面。
- Web 前端。
- 跨设备统计。
- 总控平台数据库设计。

## 2. 当前需要交给通讯工程师的文件

### 2.1 C++ 设备数据读取与共享内存写入

```text
device_agent/cpp/SharedMemoryWriter.cpp
```

当前作用：

- 示例 C++ 程序。
- 创建 Windows 共享内存。
- 构造试验箱实时 JSON 快照。
- 按统一内存布局写入共享内存。

后续要改成：

- 对接真实设备协议，例如串口、网口、PLC、Modbus、厂商 SDK。
- 读取真实温度、湿度、运行状态、步骤、告警、设备参数。
- 保持共享内存格式不变。
- 将模拟数据替换为真实设备数据。

### 2.2 共享内存读写协议工具

```text
backend/shared_memory_store.py
```

当前作用：

- 定义共享内存名称。
- 定义共享内存大小。
- 定义头部结构。
- 提供 Python 侧创建、读取、写入、调试共享内存的方法。

后续建议：

- 这个文件虽然现在放在 `backend/`，但职责属于设备端。
- 后续应迁移到设备端目录，例如 `apps/device-edge/agent/shared_memory_store.py`。
- C++ 写入逻辑必须和这里的读取逻辑保持一致。

### 2.3 Python 模拟写入程序

```text
device_memory_writer.py
device_memory_writer_cn.py
```

当前作用：

- 模拟设备实时数据。
- 调用 `backend/shared_memory_store.py` 写共享内存。
- 方便没有真实 C++ 程序时测试上传链路。

后续定位：

- 只作为调试工具。
- 真实项目中由 C++ 上位机替代。
- 通讯工程师可以用它对照 JSON 字段和共享内存格式。

### 2.4 设备端上传服务

```text
device_memory_uploader.py
```

当前作用：

- 读取本机共享内存。
- 将快照包装成上传请求。
- POST 到总控平台。

后续要增强：

- 增加本地缓存。
- 增加本地数据库落库。
- 增加断线重试。
- 增加上传失败补偿。
- 增加身份认证 token。
- 增加指令拉取或长连接接收。
- 增加指令执行结果回传。
- 增加设备端日志。

## 3. 不建议整体交给通讯工程师的文件

```text
backend/memory_router.py
backend/main.py
frontend-vue/
web/
```

说明：

- `backend/memory_router.py` 里面的 `POST /api/device-ingest/snapshots` 可以作为总控接收接口参考。
- 但它同时包含本机共享内存读取、WebSocket、页面入口，职责混杂，不应该整体交给通讯工程师维护。
- `backend/main.py` 是端到端模拟 Demo，不是正式设备端。
- `frontend-vue/` 和 `web/` 是用户访问端，不属于通讯工程师范围。

## 4. 共享内存协议

共享内存名称：

```text
industrial_chamber_realtime_v1
```

共享内存大小：

```text
256 KB
```

内存布局：

```text
0      ~ 7      uint64 version
8      ~ 11     uint32 payload_length
12     ~ end    UTF-8 JSON payload
```

写入约定：

```text
version 为奇数：正在写入
version 为偶数：数据稳定，可以读取
payload_length：JSON 字节长度，不是字符长度
payload：UTF-8 编码 JSON
```

C++ 写入顺序：

```text
1. 将 version 设置为下一个奇数
2. 将 payload_length 设置为 0
3. 写入 JSON payload
4. 写入 payload_length
5. 将 version 设置为下一个偶数
```

Python 读取顺序：

```text
1. 读取 version_before 和 payload_length
2. 如果 version_before 是奇数，说明正在写入，稍后重试
3. 按 payload_length 读取 JSON
4. 再读一次 version_after
5. 如果 version_before == version_after 且为偶数，说明本次读取稳定
```

## 5. 实时快照 JSON 格式

C++ 每次写入完整快照，不写增量片段。

示例：

```json
{
  "source": "cpp_shared_memory_writer",
  "sequence": 1024,
  "written_at": 1782977408.489408,
  "devices": [
    {
      "device_id": "CH-001",
      "name": "温湿度试验箱 1",
      "ip_address": "192.168.1.101",
      "online": true,
      "run_state": "RUNNING",
      "current_temperature": -20.4,
      "current_humidity": 40.2,
      "target_temperature": -20,
      "target_humidity": 40,
      "current_step": 1,
      "total_steps": 3,
      "alarm": null,
      "updated_at": 1782977408.489408
    }
  ]
}
```

字段要求：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source` | string | 数据来源，例如 `cpp_shared_memory_writer` |
| `sequence` | integer | 快照序号，每次递增 |
| `written_at` | number | C++ 写入时间，Unix 秒 |
| `devices` | array | 当前工控机管理的设备列表 |
| `device_id` | string | 设备编号，全平台唯一或结合 `edge_id` 唯一 |
| `name` | string | 设备名称 |
| `ip_address` | string | 设备 IP，可选但建议提供 |
| `online` | bool | 是否在线 |
| `run_state` | string | 运行状态 |
| `current_temperature` | number | 当前温度 |
| `current_humidity` | number | 当前湿度 |
| `target_temperature` | number | 目标温度 |
| `target_humidity` | number | 目标湿度 |
| `current_step` | integer | 当前步骤 |
| `total_steps` | integer | 总步骤数 |
| `alarm` | string/null | 当前告警 |
| `updated_at` | number | 当前设备数据更新时间，Unix 秒 |

运行状态建议使用以下枚举：

```text
OFFLINE
IDLE
READY
WAIT_LOCAL_CONFIRM
RUNNING
PAUSED
COMPLETED
STOPPED
STOPPING
ABORTING
ALARM
MAINTENANCE
```

## 6. 上传总控平台

当前上传接口：

```http
POST /api/device-ingest/snapshots
```

请求体：

```json
{
  "edge_id": "EDGE-CHAMBER-001",
  "agent_version": "0.1.0",
  "uploaded_at": 1782977408.489408,
  "snapshot": {
    "source": "cpp_shared_memory_writer",
    "sequence": 1024,
    "written_at": 1782977408.489408,
    "devices": []
  }
}
```

返回：

```json
{
  "status": "accepted",
  "edge_id": "EDGE-CHAMBER-001",
  "received_at": 1782977408.600001,
  "device_count": 4,
  "sequence": 1024
}
```

设备端上传服务要求：

- 上传频率建议先按 500ms 到 1000ms 一次。
- 上传失败不能丢数据，应先写本地缓存。
- 网络恢复后按时间顺序补传。
- 每台工控机必须配置唯一 `edge_id`。
- 请求头后续应增加认证 token。
- 日志中记录上传成功、失败、重试、丢弃原因。

## 7. 本地缓存和本地落库

当前项目还没有正式实现本地缓存和本地数据库，这是通讯工程师需要补齐的部分。

建议实现：

```text
MySQL 本地数据库
  edge_snapshots
    id
    edge_id
    sequence
    written_at
    uploaded_at
    payload_json
    upload_status
    retry_count
    last_error
    created_at
    updated_at

  command_results
    id
    edge_id
    command_id
    device_id
    status
    message
    payload_json
    reported_at
    upload_status
    retry_count
```

设备端本地 MySQL 定位：

- 每台工控机本地安装或连接一套 MySQL。
- 本地 MySQL 主要用于断网缓存、上传失败补偿、最近数据追溯和通讯排查。
- 总控平台的 MySQL 仍然是中心库，两者职责不同。
- 设备端恢复网络后，将本地 MySQL 中未上传的数据按时间顺序补传到总控平台。

缓存规则：

- 每次从共享内存读到稳定快照后，先写本地库。
- 上传成功后标记为 `UPLOADED`。
- 上传失败保留为 `PENDING` 或 `FAILED_RETRYABLE`。
- 定时扫描未上传记录并补传。
- 设置最大保留时间或最大容量，避免磁盘无限增长。

## 8. 接收总控指令

当前项目还没有正式实现设备端接收总控指令，需要新增。

建议先用轮询方式，稳定后再考虑 WebSocket 或 MQTT。

### 8.1 拉取待执行指令

建议接口：

```http
GET /api/device-commands/pending?edge_id=EDGE-CHAMBER-001
```

返回：

```json
{
  "commands": [
    {
      "command_id": "CMD-001",
      "device_id": "CH-001",
      "command_type": "START_TEST",
      "created_at": 1782977408.489408,
      "payload": {
        "recipe_name": "High Low Temperature Cycle",
        "steps": []
      }
    }
  ]
}
```

### 8.2 执行指令

设备端处理流程：

```text
1. 拉取待执行指令
2. 校验 command_id 是否已经处理过，避免重复执行
3. 校验 device_id 是否属于当前工控机
4. 将业务指令转换成 C++ 或设备控制程序可识别的本地指令
5. 必要时等待本机人工确认
6. 执行设备通讯
7. 记录本地执行日志
8. 回传执行结果
```

常见指令类型：

```text
START_TEST
STOP_TEST
PAUSE_TEST
RESUME_TEST
SET_TARGET
DOWNLOAD_RECIPE
ACK_ALARM
```

### 8.3 回传指令结果

建议接口：

```http
POST /api/device-commands/results
```

请求体：

```json
{
  "edge_id": "EDGE-CHAMBER-001",
  "command_id": "CMD-001",
  "device_id": "CH-001",
  "status": "EXECUTED",
  "message": "started",
  "reported_at": 1782977408.489408,
  "payload": {}
}
```

状态建议：

```text
RECEIVED
LOCAL_CONFIRM_REQUIRED
EXECUTING
EXECUTED
REJECTED
FAILED
TIMEOUT
```

## 9. 推荐运行方式

### 9.1 编译 C++ 示例

```powershell
cd D:\industrial-chamber-platform\device_agent\cpp
cl /std:c++17 /EHsc SharedMemoryWriter.cpp
```

运行：

```powershell
.\SharedMemoryWriter.exe
```

### 9.2 启动 Python 模拟写入

如果暂时没有 C++ 程序，可用 Python 模拟：

```powershell
cd D:\industrial-chamber-platform
python device_memory_writer_cn.py
```

### 9.3 启动设备端上传服务

```powershell
cd D:\industrial-chamber-platform
python device_memory_uploader.py --edge-id EDGE-CHAMBER-001 --server http://127.0.0.1:8010 --interval 0.5
```

## 10. 通讯工程师最终交付物

建议最终交付：

- 真实 C++ 设备采集程序。
- 共享内存写入模块。
- 设备端上传服务。
- 本地 MySQL 缓存/落库。
- 断线重试和补传机制。
- 指令拉取模块。
- 指令执行结果回传模块。
- 配置文件示例。
- 设备端运行日志。
- 部署说明。
- 与总控平台联调说明。

## 11. 最重要的边界

通讯工程师只需要保证：

```text
真实设备数据
  -> C++ 采集
  -> 共享内存
  -> 设备端上传服务
  -> 总控平台接收接口
```

以及：

```text
总控平台指令
  -> 设备端上传服务拉取或接收
  -> C++ 或设备控制程序执行
  -> 执行结果回传总控平台
```

只要这两条链路稳定，多设备管理、用户页面、报表和权限都由平台端继续完成。
