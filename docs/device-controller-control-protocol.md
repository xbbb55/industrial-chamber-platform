# 工控机控制 JSON 协议适配

本项目按照《JSON接口说明》将工控机控制指令分为 FE_W 和 BE_R：

```json
{"command":"Run","time":"2026-07-22 15:30:53"}
```

设备完成后返回：

```json
{"successMessage":"Run","time":"2026-07-22 15:30:54"}
```

支持的 FE_W 命令：

| 操作 | command |
| --- | --- |
| 启动 | `Run` |
| 停止 | `Stop` |
| 保持 | `Hold` |
| 继续 | `Keep` |
| 跳段 | `Jnmp` |
| 蜂鸣器开/关 | `BuzzerON` / `BuzzerOFF` |
| 报警复位 | `Reset` |
| 模式切换 | `RunMode=1` / `RunMode=2` |
| 定值更新 | `fixed_value` |
| 下载程序 | `DownloadProgram=程序号` |
| 保护/其它设定 | `operation_setting` |
| 基础信息 | `basic_info` |
| 测量校正 | `correction` |
| PID | `pid_set` |
| 出厂参数 | `factory_params` |

总控接口与设备长连接：

- `POST /api/devices/{device_id}/commands`：用户端创建 FE_W 指令。
- `WS /api/edge/ws`：设备端接收 `{ "type": "command" }`，并通过 `{ "type": "command_result" }` 回传执行结果。

设备端不再提供 HTTP 拉取或回传接口，所有设备通讯只使用该 WebSocket 长连接。
