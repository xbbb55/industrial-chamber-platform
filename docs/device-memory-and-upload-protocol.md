# 环境试验箱边缘端共享内存与总控接入协议

## 1. 责任边界

外部 C++ 通讯程序负责采集真实设备数据和执行实际控制；`device_edge` 负责共享内存桥接、本地 API、本地记录，以及可选的总控 WebSocket 连接。

```text
C++ 通讯程序 -> BE_W -> device_edge -> 本机 Vue 看板
C++ 通讯程序 <- FE_W <- device_edge
C++ 通讯程序 -> BE_R -> device_edge
device_edge <-> WS /api/edge/ws <-> 总控平台
```

## 2. 共享内存

默认存在三块 Windows 共享内存，名称和大小由 `device-edge.config.json` 配置：

```text
BE_W  实时设备 JSON，C++ 写入，device_edge 读取
FE_W  控制命令 JSON，device_edge 写入，C++ 读取并清空
BE_R  命令执行状态 JSON，C++ 写入，device_edge 读取
```

生产默认采用 `length_prefixed_json_v1`：映射容量为 4096 字节，偏移 `0~3` 为小端序 `uint32` JSON 字节长度，偏移 `4` 起为 UTF-8 JSON。

## 3. 实时数据

`BE_W` 写入完整的单设备工控 JSON 根对象。关键字段包括：

```text
device_id、time、status、timeData、program、mainData、compressor、DUT、event
```

`device_edge.snapshot_normalizer` 将该对象转换为用户端和总控统一使用的设备快照，包括设备状态、温湿度、目标值、步骤和告警。

## 4. 控制数据

`FE_W` 的最小格式：

```json
{"command":"Run","time":"2026-08-30 10:00:00"}
```

`BE_R` 的最小格式：

```json
{"successMessage":"Run","time":"2026-08-30 10:00:01"}
```

命令映射及安全边界见 [device-controller-control-protocol.md](device-controller-control-protocol.md)。

## 5. 总控接入

配置 `control_center.enabled=true` 后，边缘端连接总控的 `WS /api/edge/ws`，上传实时快照、接收待执行命令并回传执行结果。总控只消费标准快照和命令协议，不直接访问工控机共享内存。
