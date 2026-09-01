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

## C++ 原生共享内存协议

当前工控机 C++ 程序使用 Windows 原生 `CreateFileMappingW` / `MapViewOfFile`。三块映射的容量均为 `4096` 字节，数据格式固定为：

```text
偏移 0~3：uint32 小端序 JSON 字节长度
偏移 4 起：UTF-8 JSON
```

`device-edge.config.json` 必须设置：

```json
{
  "shared_memory_name": "BE_W",
  "command_request_memory_name": "FE_W",
  "command_status_memory_name": "BE_R",
  "shared_memory_size": 4096,
  "command_request_memory_size": 4096,
  "command_status_memory_size": 4096,
  "shared_memory_protocol": "length_prefixed_json_v1"
}
```

本地命名映射只在同一个 Windows 会话中可见。若 C++ 与 `device_edge` 无法在同一会话运行，双方必须统一使用 `Global\\BE_W`、`Global\\FE_W`、`Global\\BE_R`。

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
GET /api/settings/fixed-value
PUT /api/settings/fixed-value

定值模式参数保存到本机 MySQL `HDQC.fixed_value`，固定使用 `id=1` 保存当前配置，重复保存会更新该记录。数据库密码不写入配置文件，启动服务前设置配置中 `password_env` 指定的环境变量，例如：

```powershell
$env:MYSQL_PWD = "你的数据库密码"
python -m device_edge.run_edge serve --config device-edge.config.json --host 127.0.0.1 --port 8765
```
```

Vue 开发环境默认代理到 `http://127.0.0.1:8765`。生产环境构建 `frontend-vue` 后，`device_edge` 会托管 `frontend-vue/dist` 中的静态文件。

## 登录账户（MySQL）

首次调用登录接口时，服务会在配置的 MySQL 数据库（默认 `HDQC`）中创建 `accounts` 表，并按环境变量写入管理员账户：

```powershell
$env:MYSQL_PWD = "你的数据库密码"
$env:AUTH_SEED_USERNAME = "admin"          # 可选，默认 admin
$env:AUTH_SEED_PASSWORD = "12345"          # 可选，默认 12345，仅用于本地开发
```

连接参数可通过 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、`MYSQL_USER` 配置。当前密码规则为至少 5 位数字；管理员可创建用户并分配管理员、工程师或销售权限组，三种权限组目前拥有相同的设备业务权限。

## 命令协议

`device_edge` 接收前端或总控命令后，先进行本地操作员白名单校验，再向 `FE_W` 写入当前 C++ 协议的命令。C++ 每 200ms 读取一次，读取后必须清空命令内容，再执行设备动作。C++ 不负责用户权限判断，但必须自行完成命令码、设备状态和参数范围的安全校验。

当前 `FE_W` 与 `BE_R` 维持既有协议：

保持时写入 `HoldON`，继续时写入 `HoldOFF`；跳步时写入 `Jump`。

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
