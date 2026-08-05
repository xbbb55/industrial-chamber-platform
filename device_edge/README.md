# 工控机设备端运行说明

这个目录是可以单独放到工控机本地运行的设备端程序。它只负责：

- 模拟读取设备数据。
- 写入 Windows 共享内存。
- 写入工控机本地 MySQL 缓存。
- 向你电脑上的总服务端上传数据。
- 上传失败后保留本地记录，网络恢复后补传。

## 1. 目录内容

```text
device_edge/
  config.example.json       配置模板
  requirements.txt          工控机 Python 依赖
  run_edge.py               入口命令
  simulator.py              模拟设备数据读取
  shared_memory_store.py    共享内存读写协议
  mysql_store.py            本地 MySQL 缓存
  websocket_client.py       长连接、实时上报与指令执行
```

## 2. 总服务端在你电脑上启动

在你的电脑上启动总服务端：

```powershell
cd D:\industrial-chamber-platform
python -m uvicorn backend.memory_router:app --host 0.0.0.0 --port 8010
```

工控机配置里的 `server_url` 要写你电脑的局域网 IP，例如：

```json
"server_url": "http://192.168.1.20:8010"
```

## 3. 工控机准备 MySQL

在工控机本地 MySQL 创建数据库：

```sql
CREATE DATABASE industrial_device_edge DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

程序启动时会自动创建 `edge_snapshots` 表。

## 4. 工控机安装依赖

```powershell
cd D:\industrial-chamber-platform\device_edge
python -m pip install -r requirements.txt
```

## 5. 生成配置

```powershell
cd D:\industrial-chamber-platform
python -m device_edge.run_edge init-config --config device-edge.config.json
```

编辑 `device-edge.config.json`：

- `edge_id`：每台工控机唯一。
- `server_url`：你电脑的总服务端地址。
- `mysql.host`、`mysql.user`、`mysql.password`、`mysql.database`：工控机本地 MySQL。

## 6. 启动模拟端

```powershell
cd D:\industrial-chamber-platform
python -m device_edge.run_edge manual-ui --config device-edge.config.json --host 0.0.0.0 --port 8765
```

这个命令会同时启动本地模拟界面、共享内存写入、总服务端上传、命令接收和命令回执。

不要再单独启动上传进程，否则同一个 `edge_id` 会建立重复长连接。

## 8. 总服务端查看实时数据

在浏览器打开：

```text
http://你的电脑IP:8010/api/memory/snapshot
```

如果能看到 `EDGE-CHAMBER-001` 对应的设备快照，说明 WebSocket 链路已打通。

## 9. 后续接真实设备

后续通讯工程师只需要替换 `simulator.py` 的模拟读取逻辑，或用 C++ 程序按同样的共享内存格式写入数据。

Edge Agent 不关心真实设备协议，只需要稳定读取共享内存，并通过 WebSocket 与总服务端交换数据和指令。
