# 工业试验箱平台架构职责拆分

## 1. 拆分目标

后续系统建议明确拆成三个独立责任域：

```text
单设备通讯端 / 设备边缘端
  负责：读取设备 C++ 数据、单设备上位通讯、本地缓存/落库、向总控发送数据、接收并转交总控指令

多设备联合管理端 / 总控平台
  负责：接收多台设备或多台工控机数据、统一设备台账、实时状态、历史查询、告警、权限、指令调度

用户访问端
  负责：浏览器或大屏访问、设备列表、设备详情、曲线、告警、报表、操作入口
```

核心原则：用户访问端不直接连接单设备；多设备管理端不直接读取某台工控机的共享内存；单设备通讯端不处理跨设备业务。

## 2. 当前代码归属

### 单设备通讯端

当前相关文件：

```text
device_agent/cpp/SharedMemoryWriter.cpp
device_memory_writer.py
device_memory_writer_cn.py
device_memory_uploader.py
backend/shared_memory_store.py
```

职责说明：

- C++ 上位机或采集程序读取设备实时数据。
- C++ 将当前完整快照写入 Windows 共享内存。
- 设备端上传服务读取本机共享内存。
- 上传服务负责本地缓存、断线重试、必要时写本地数据库。
- 上传服务通过 HTTP、MQTT 或消息队列把数据发送到总控平台。
- 上传服务接收总控指令后，交给本机 C++ 上位机或设备控制程序处理。

后续这部分可以整体交给通讯工程师维护。

### 多设备联合管理端

当前相关文件：

```text
backend/memory_router.py
backend/main.py
```

职责说明：

- `backend.main` 当前是端到端模拟，把设备模拟、指令队列、管理接口混在一起，只适合 Demo。
- `backend.memory_router` 通过 `WS /api/edge/ws` 接收设备端数据和执行结果；它同时读取本机共享内存的 Demo 逻辑后续应拆开。
- 总控平台只接收设备通讯端上传的数据，不关心底层 C++ 如何采集。
- 总控平台统一维护设备、工控机、实时状态、历史数据、告警、试验任务、用户权限。
- 总控平台向用户访问端提供 HTTP API 和 WebSocket。

### 用户访问端

当前相关文件：

```text
frontend-vue/
web/
```

职责说明：

- `frontend-vue` 是后续主用户端。
- `web` 是早期静态测试页面，可作为调试页保留或逐步下线。
- 用户端只访问总控平台 API。
- 用户端不直接读取共享内存，不直接访问设备端上传服务。

## 3. 推荐目标目录

建议逐步整理成以下结构：

```text
industrial-chamber-platform/
  apps/
    device-edge/
      cpp/
        SharedMemoryWriter.cpp
      agent/
        shared_memory_store.py
        uploader.py
        local_cache.py
        command_client.py
        config.example.yaml
      docs/
        edge-protocol.md

    control-center/
      backend/
        main.py
        api/
          ingest.py
          devices.py
          commands.py
          alarms.py
          reports.py
        services/
          device_registry.py
          realtime_state.py
          command_dispatcher.py
          history_writer.py
        storage/
          redis_store.py
          mysql_models.py
      docs/
        ingest-api.md

    user-web/
      frontend-vue/

  docs/
    architecture-responsibility-split.md
```

当前阶段不一定要一次性搬目录，但代码责任要按这个边界演进。

## 4. 数据流

### 实时数据上行

```text
设备硬件
  -> C++ 上位机采集
  -> Windows 共享内存
  -> 设备端上传服务
  -> 总控平台接收 API
  -> Redis 实时状态 / MySQL 历史记录
  -> WebSocket / HTTP API
  -> 用户访问端
```

边界约束：

- 共享内存只存在于单台工控机内部。
- 总控平台不读取共享内存，只接收标准上传协议。
- 用户访问端只读总控 API，不知道共享内存存在。

### 控制指令下行

```text
用户访问端发起操作
  -> 总控平台鉴权、记录、生成指令
  -> 设备端上传服务轮询或长连接接收指令
  -> C++ 上位机本地确认 / 执行
  -> 设备端回传执行结果
  -> 总控平台更新任务状态
  -> 用户访问端看到结果
```

边界约束：

- 总控平台只发“业务指令”，不直接操作设备寄存器。
- C++ 或设备通讯端负责把业务指令转换为设备实际通讯协议。
- 对于启停、配方下发等危险操作，应保留本机确认或权限校验。

## 5. 设备端交接范围

通讯工程师建议负责以下内容：

- 设备协议通讯：串口、网口、PLC、Modbus、厂商 SDK 等。
- C++ 采集程序：读取温度、湿度、状态、步骤、告警、设备参数。
- 共享内存写入：按统一 JSON 快照格式输出。
- 设备端上传服务：读取共享内存、本地缓存、断线重试、上传总控。
- 本地数据库写入：用于断网缓存、最近数据追溯、上传失败补偿。
- 指令接收与转发：接收总控指令，并交给 C++ 或设备控制程序。
- 设备端日志：采集日志、上传日志、通讯异常日志。

通讯工程师不需要负责：

- 多设备统一管理页面。
- 总控用户权限。
- 跨设备统计。
- 总控历史报表。
- Web 前端交互。

## 6. 总控平台负责范围

平台后端建议负责以下内容：

- 接收所有设备端上传的数据。
- 校验 `edge_id`、设备身份、token、数据格式。
- 维护设备台账：工控机、设备、通道、所属区域、在线状态。
- 维护实时状态：建议 Redis 保存最新快照。
- 写入历史数据：建议 MySQL 或时序库保存关键点位与事件。
- 提供用户端 API：设备列表、设备详情、曲线、告警、报表。
- 生成并追踪控制指令：指令状态包括已创建、已下发、已确认、执行中、成功、失败、超时。
- 通过 WebSocket 推送实时状态。

## 7. 用户访问端负责范围

前端建议只对接总控平台：

- 设备总览。
- 单设备详情。
- 实时温湿度曲线。
- 告警中心。
- 历史记录。
- 试验报告。
- 操作入口：启动、停止、暂停、恢复、配方下发。
- 用户登录、角色权限展示。

前端不应该包含：

- 共享内存读取逻辑。
- C++ 数据解析逻辑。
- 设备通讯协议细节。
- 本地设备 IP 直连控制逻辑。

## 8. 推荐接口契约

### 设备端 WebSocket 连接与上传快照

```text
WS /api/edge/ws
```

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

### 总控下发待执行指令

总控在同一条 WebSocket 上发送：

```json
{
  "commands": [
    {
      "command_id": "CMD-001",
      "device_id": "CH-001",
      "command_type": "START_TEST",
      "created_at": 1782977408.489408,
      "payload": {}
    }
  ]
}
```

### 设备端回传指令结果

设备端在同一条 WebSocket 上发送：

```json
{
  "edge_id": "EDGE-CHAMBER-001",
  "command_id": "CMD-001",
  "device_id": "CH-001",
  "status": "EXECUTED",
  "message": "started",
  "reported_at": 1782977408.489408
}
```

## 9. 近期改造建议

第一步：保留现有 Demo，先把责任边界写入文档和接口说明。

第二步：把 `backend.shared_memory_store` 从总控后端概念中移出，归到设备端公共库。

第三步：把 `backend.memory_router` 拆成两个服务：

```text
device-edge-agent
  读取共享内存并上传

control-center-api
  只接收上传，不读取共享内存
```

第四步：总控后端引入真实存储：

```text
Redis：设备最新状态、在线心跳、WebSocket 推送缓存
MySQL：设备台账、历史数据、告警、指令、操作日志
```

第五步：前端从 `/ws/memory` 切换到总控 WebSocket，例如：

```text
WS /ws/devices/overview
WS /ws/devices/{device_id}
```

## 10. 最终边界一句话

通讯工程师交付“单设备数据采集、缓存、上传、指令落地执行”；平台后端交付“多设备统一接入、存储、调度、权限和推送”；前端交付“用户可视化访问和操作入口”。
