# 环境试验箱设备端共享内存与 FastAPI 上传协议

## 1. 目标

每台环境试验箱工控机本地运行两个角色：

```text
C++ 上位机
  -> 采集设备数据
  -> 整理为标准 JSON
  -> 写入 Windows 共享内存

设备端上传服务
  -> 读取本机共享内存
  -> 通过 HTTP POST 上传到总控 FastAPI
```

总控端负责接收每台工控机上传的数据，并向 Web 管理端提供设备列表、实时状态、历史查询和控制申请能力。

## 2. 共享内存命名

当前测试项目使用固定共享内存名称：

```text
industrial_chamber_realtime_v1
```

每台工控机本机内部可以使用相同名称，因为共享内存只在本机进程之间共享。不同工控机之间通过 FastAPI 上传区分 `edge_id`。

## 3. 共享内存布局

共享内存总大小：

```text
256 KB
```

内存结构：

```text
0      ~ 7      uint64 version
8      ~ 11     uint32 payload_length
12     ~ end    UTF-8 JSON payload
```

约定：

```text
version 为奇数：C++ 正在写入
version 为偶数：数据稳定，路由端可以读取
payload_length：JSON 字节长度，不是字符数
payload：UTF-8 编码的 JSON
```

写入顺序：

```text
1. 将 version 设置为奇数
2. 将 payload_length 设置为 0
3. 写入 JSON payload
4. 写入 payload_length
5. 将 version 设置为下一个偶数
```

读取顺序：

```text
1. 读取 version_before 和 payload_length
2. 如果 version_before 是奇数，说明正在写，稍后重试
3. 按 payload_length 读取 JSON
4. 再读取 version_after
5. 如果 version_before == version_after 且为偶数，说明本次读取稳定
```

## 4. JSON 快照格式

C++ 上位机每次写入的是完整快照，不是增量片段。

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

字段说明：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source` | string | 数据来源，例如 `cpp_shared_memory_writer` |
| `sequence` | integer | 写入序号，每次写入递增 |
| `written_at` | number | Unix 时间戳，秒 |
| `devices` | array | 当前工控机管理的设备列表 |
| `device_id` | string | 设备编号 |
| `name` | string | 设备名称 |
| `online` | bool | 是否在线 |
| `run_state` | string | 运行状态 |
| `current_temperature` | number | 当前温度 |
| `current_humidity` | number | 当前湿度 |
| `target_temperature` | number | 目标温度 |
| `target_humidity` | number | 目标湿度 |
| `current_step` | integer | 当前步骤 |
| `total_steps` | integer | 总步骤数 |
| `alarm` | string/null | 当前报警 |
| `updated_at` | number | 设备数据更新时间 |

## 5. 运行状态枚举

建议统一使用以下英文枚举作为协议值，前端再映射为中文：

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

## 6. C++ 示例

示例文件：

```text
device_agent/cpp/SharedMemoryWriter.cpp
```

它完成了：

```text
1. 创建 Windows 共享内存
2. 构造环境试验箱 JSON 快照
3. 按 version + payload_length + payload 格式写入共享内存
4. 每 200ms 写入一次
```

MSVC 编译：

```powershell
cd D:\industrial-chamber-platform\device_agent\cpp
cl /std:c++17 /EHsc SharedMemoryWriter.cpp
```

运行：

```powershell
.\SharedMemoryWriter.exe
```

## 7. 设备端上传服务

示例文件：

```text
device_memory_uploader.py
```

它完成了：

```text
1. 读取本机共享内存
2. 将快照包装成上传请求
3. POST 到总控 FastAPI
```

启动：

```powershell
python device_memory_uploader.py --edge-id EDGE-CHAMBER-001 --server http://127.0.0.1:8010
```

上传接口：

```text
POST /api/device-ingest/snapshots
```

上传 JSON：

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

总控返回：

```json
{
  "status": "accepted",
  "edge_id": "EDGE-CHAMBER-001",
  "received_at": 1782977408.600001,
  "device_count": 4,
  "sequence": 1024
}
```

## 8. 总控查看上传结果

接口：

```text
GET /api/device-ingest/latest
```

返回所有已经上传到总控的工控机快照：

```json
{
  "edge_count": 1,
  "edges": {
    "EDGE-CHAMBER-001": {
      "edge_id": "EDGE-CHAMBER-001",
      "received_at": 1782977408.600001,
      "snapshot": {}
    }
  }
}
```

## 9. 正式项目建议

第一阶段可以沿用当前模式：

```text
C++ 上位机写共享内存
Python 设备端上传服务读取共享内存
上传到总控 FastAPI
```

第二阶段再增强：

```text
1. 上传服务增加断线重试
2. 增加本地缓存，网络断开时暂存最近数据
3. 增加设备身份认证 token
4. 总控写入 Redis latest
5. 总控批量写 MySQL 历史数据
6. WebSocket 按设备订阅推送
```

关键边界：

```text
C++ 负责采集和本机控制
共享内存负责本机跨进程实时交换
上传服务负责和总控通信
FastAPI 总控负责统一接收、权限、路由和推送
```
