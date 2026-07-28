# Industrial Chamber Platform Test Project

This is a minimal end-to-end test project for the environmental chamber architecture.

It verifies the core loop:

```text
simulated C++ device agent
  -> in-memory realtime broker
  -> FastAPI routes and WebSocket
  -> browser dashboard
  -> control request
  -> simulated device command queue
  -> execution result back to browser
```

For this first test, Redis and MySQL are intentionally replaced by in-process memory structures so the line can be tested quickly. After the workflow is proven, replace:

- `latest_state` with Redis Hash/String
- `event_queues` with Redis Stream/PubSub
- `control_requests` with MySQL persistence

## Run

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the server:

```powershell
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Shared Memory Test

This is the closer simulation for your target architecture:

```text
process 1: device_memory_writer.py
  -> writes realtime chamber data into Windows shared memory

process 2: backend.memory_router
  -> reads shared memory
  -> exposes HTTP routes
  -> pushes snapshots to WebSocket clients

browser:
  -> opens the management frontend
  -> reads data through the router
```

Start the memory writer in terminal 1:

```powershell
python device_memory_writer_cn.py
```

模拟器现在写入生产工控 JSON 的单设备根对象（`DUT`、`compressor`、`mainData`、`program`、`status`、`timeData`）。默认设备号为 `SIM-PY-CN-001`，可通过环境变量切换：

```powershell
$env:CHAMBER_DEVICE_ID = "SIM-PY-CN-002"
python device_memory_writer_cn.py
```

Start the router in terminal 2:

```powershell
python -m uvicorn backend.memory_router:app --host 127.0.0.1 --port 8010
```

Open:

```text
http://127.0.0.1:8010
```

Useful APIs:

```text
GET /api/memory/snapshot
GET /api/memory/devices
WS  /ws/memory
```

## Vue Industrial Dashboard

新的客户端看板位于 `frontend-vue`，用于模拟最终浏览器/桌面端管理界面。它通过 Vite 代理访问本机 FastAPI：

```text
Vue dashboard: http://127.0.0.1:5173
FastAPI router: http://127.0.0.1:8010
WebSocket:      ws://127.0.0.1:8010/ws/memory
```

首次运行安装依赖：

```powershell
cd D:\industrial-chamber-platform\frontend-vue
npm install
```

启动前端开发服务：

```powershell
npm run dev
```

局域网其它电脑访问时，先确保后端使用 `--host 0.0.0.0` 启动，再访问：

```text
http://本机IP:5173
```

生产构建验证：

```powershell
npm run build
```

## What To Test

1. Watch three simulated chambers update in realtime.
2. Open a chamber card to see status, temperature, humidity, step, and alarms.
3. Click `Start Test`.
4. The request goes through FastAPI, reaches the simulated device worker, starts running, and pushes results back to the browser.
5. Click `Stop` to send a stop request through the same control path.
