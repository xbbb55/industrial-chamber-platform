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

HTTP 适配接口：

- `POST /api/devices/{device_id}/commands`：按 `command` 创建 FE_W 指令。
- `GET /api/device-commands/fe-w?edge_id=...`：设备端读取精确 FE_W JSON。
- `POST /api/device-commands/be-r?edge_id=...`：设备端提交精确 BE_R JSON。

旧的启动、停止、保持、跳步 REST 接口仍保留，但内部已经转换为上述协议。
