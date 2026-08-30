# Industrial Chamber Platform

该仓库保留工控机边缘服务、Vue 本机看板与可选总控原型。设备采集与实际控制由外部 C++ 通讯程序负责；该程序通过 Windows 共享内存与 `device_edge` 交互。

```text
C++ 通讯程序
  -> BE_W（实时数据） -> device_edge -> 本机 HTTP / WebSocket -> Vue 看板
  <- FE_W（控制请求） <- device_edge
  -> BE_R（执行结果） -> device_edge

device_edge --可选 WebSocket--> backend.memory_router（多设备总控原型）
```

## 本机边缘服务

安装边缘服务依赖：

```powershell
python -m pip install -r device_edge/requirements.txt
```

复制并配置边缘服务配置文件：

```powershell
python -m device_edge.run_edge init-config --config device-edge.config.json
```

确认 C++ 通讯程序已经创建 `BE_W` 和 `BE_R` 后，启动本机服务：

```powershell
python -m device_edge.run_edge serve --config device-edge.config.json --host 0.0.0.0 --port 8765
```

详细的共享内存、命令和数据库配置见 [device_edge/README.md](device_edge/README.md)。

## Vue 工业看板

开发环境下，Vite 默认代理到本机 `device_edge`：

```powershell
cd D:\industrial-chamber-platform\frontend-vue
npm install
npm run dev
```

看板地址为 `http://127.0.0.1:5173`。生产部署前执行：

```powershell
npm run build
```

构建后的 `frontend-vue/dist` 会由 `device_edge` 托管。

## 可选总控原型

多设备总控服务接收各边缘端的 WebSocket 上传，聚合实时设备状态，并向边缘端下发命令：

```powershell
python -m uvicorn backend.memory_router:app --host 0.0.0.0 --port 8010
```

边缘端配置中设置 `control_center.enabled=true` 和总控地址后，会连接 `WS /api/edge/ws`。当前总控原型仍使用进程内实时状态和命令记录，尚未接入 Redis/MySQL 持久化。
