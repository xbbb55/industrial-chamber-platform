# 通讯工程师交接说明：单设备通讯端

## 1. 交接范围

通讯工程师负责外部 C++ 通讯程序与 `device_edge` 的本机集成：读取真实控制器数据，向共享内存写实时快照，读取控制命令，执行后写回执行状态。

```text
C++ 通讯程序 -> BE_W -> device_edge
C++ 通讯程序 <- FE_W <- device_edge
C++ 通讯程序 -> BE_R -> device_edge
```

## 2. 仓库内设备端文件

```text
device_edge/config.example.json
device_edge/config.py
device_edge/control_protocol.py
device_edge/shared_memory_store.py
device_edge/snapshot_normalizer.py
device_edge/runtime.py
device_edge/sqlite_store.py
device_edge/websocket_client.py
device_edge/local_service.py
device_edge/run_edge.py
```

其中 `runtime.py` 是共享内存、本地 SQLite、命令状态和 WebSocket 订阅的运行时；`websocket_client.py` 用于可选总控接入；`control_protocol.py` 负责控制命令映射。

## 3. 共享内存契约

默认使用 `length_prefixed_json_v1`，三块映射容量均为 4096 字节：

```text
BE_W：实时设备 JSON
FE_W：命令请求 JSON
BE_R：命令执行结果 JSON
```

偏移 `0~3` 为小端序 `uint32` JSON 字节长度，偏移 `4` 起为 UTF-8 JSON。名称、容量和协议必须与 `device-edge.config.json` 一致。

实时数据根对象应包含 `device_id`、`mainData`、`program`、`status`、`timeData`，以及按设备需要提供的 `DUT`、`compressor` 和 `event`。完整字段字典见 [../wj/数据监控.xlsx](../wj/数据监控.xlsx)。

## 4. 命令契约

边缘服务把本机或总控请求转换为 `FE_W` 的最小 JSON：

```json
{"command":"Run","time":"2026-08-30 10:00:00"}
```

C++ 程序读取后必须清空命令内容，完成实际设备侧安全校验和执行；再向 `BE_R` 写入：

```json
{"successMessage":"Run","time":"2026-08-30 10:00:01"}
```

支持的命令及参数约束见 [device-controller-control-protocol.md](device-controller-control-protocol.md)。

## 5. 启动与验收

1. C++ 通讯程序先创建并写入 `BE_W`，并创建 `BE_R`。
2. 复制配置并填写共享内存、MySQL 与可选总控连接参数。
3. 执行 `python -m device_edge.run_edge serve --config device-edge.config.json --host 127.0.0.1 --port 8765`。
4. 检查 `GET /api/status`、`GET /api/memory/snapshot` 和 `WS /ws/memory`。
5. 通过 `POST /api/devices/{device_id}/commands` 下发命令，核对 C++ 已清空 `FE_W` 且 `BE_R` 回传结果。

## 6. 不在交接范围内

`backend/memory_router.py` 是多设备总控原型，`frontend-vue/` 是用户访问端。两者不负责读取或写入单台工控机的共享内存。
