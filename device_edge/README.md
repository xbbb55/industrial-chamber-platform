# 工控机本地设备边缘服务

`device_edge` 是工控机上唯一的 Python 后端服务。生产环境中它不生成设备数据，也不直接执行设备协议；通讯工程师提供的 C++ 应用层负责设备采集与实际控制。

```text
C++ 应用层
  -> BE_W：实时数据共享内存（C++ 写，device_edge 读）
  <- FE_W：命令请求共享内存（device_edge 写，C++ 每 200ms 读）
  -> BE_R：命令状态共享内存（C++ 写，device_edge 读）

device_edge
  -> 本机 HTTP / WebSocket API
  -> 本地 SQLite
  -> 可选：总控 WebSocket 上传与命令接收
```

## 生产启动

安装依赖：

```powershell
python -m pip install -r device_edge/requirements.txt
```

生成并编辑配置：

```powershell
python -m device_edge.run_edge init-config --config device-edge.config.json
```

默认共享内存名称：

```text
BE_W  实时数据，C++ 创建并持续写入
FE_W  命令请求，device_edge 创建并写入
BE_R  命令状态，C++ 创建并写入
```

启动本机服务：

```powershell
python -m device_edge.run_edge serve --config device-edge.config.json --host 127.0.0.1 --port 8765
```

本机接口：

```text
GET /api/memory/snapshot
GET /api/memory/devices
GET /api/status
POST /api/devices/{device_id}/commands
WS  /ws/memory
```

Vue 开发环境默认代理到 `http://127.0.0.1:8765`。生产环境构建 `frontend-vue` 后，`device_edge` 会托管 `frontend-vue/dist` 中的静态文件。

## 命令协议

`device_edge` 接收前端或总控命令后，先进行本地操作员白名单校验，再向 `FE_W` 写入当前 C++ 协议的命令。C++ 每 200ms 读取一次，读取后必须清空命令内容，再执行设备动作。C++ 不负责用户权限判断，但必须自行完成命令码、设备状态和参数范围的安全校验。

当前 `FE_W` 与 `BE_R` 维持既有协议：

```json
{"command":"Run","time":"2026-07-22 15:30:53"}
```

```json
{"successMessage":"Run","time":"2026-07-22 15:30:54"}
```

`device_edge` 允许随时写入命令。C++ 在下一次 200ms 轮询前看到多次写入时，只执行最后一条；前一次命令会被覆盖。`BE_R` 表示 C++ 实际执行的最后一条命令结果。`command_id` 仅在本机 API、Vue 状态和 SQLite 中使用，不要求 C++ 处理或回传，因此多个同名命令的逐条执行结果无法可靠区分。

## 总控开关

默认仅本机运行：

```json
"control_center": { "enabled": false }
```

需要多设备总控时，启用并填写中心主机地址：

```json
"control_center": {
  "enabled": true,
  "server_url": "http://192.168.1.20:8010"
}
```

## 模拟器

`manual-ui` 仅用于没有 C++ 时的开发测试；它会生成模拟数据并写入共享内存，不属于生产启动路径：

```powershell
python -m device_edge.run_edge manual-ui --config device-edge.config.json
```
