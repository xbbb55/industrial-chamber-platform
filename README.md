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

确认 C++ 通讯程序已经创建 `BE_W` 和 `BE_R` 后，启动本机服务。

服务启动时会执行**部署自检**：监听地址、部署版本与 Cookie 模式必须一致，否则拒绝启动。**不接受 `0.0.0.0` 裸监听**，必须显式写回环地址或具体网卡地址。

本机版（Web 端与 Electron 都只在本机打开）：

```powershell
$env:DEPLOYMENT_PROFILE = "local"
python -m device_edge.run_edge serve --config device-edge.config.json --host 127.0.0.1 --port 8765
```

多设备版（局域网内其它设备也可访问看板）。必须绑定具体网卡地址；无 HTTPS 时使用 `strict-http` 并持有书面风险接受：

```powershell
$env:DEPLOYMENT_PROFILE = "multi-device"
$env:SESSION_COOKIE_MODE = "strict-http"
python -m device_edge.run_edge serve --config device-edge.config.json --host 192.168.1.2 --port 8765
```

该入口若已部署 HTTPS 反向代理，应改用 `$env:SESSION_COOKIE_MODE = "secure"`，并把 `$env:TRUSTED_PROXY_IPS` 设为反向代理地址。

详细的共享内存、命令、数据库与部署自检说明见 [device_edge/README.md](device_edge/README.md)。

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
python -m uvicorn backend.memory_router:app --host 127.0.0.1 --port 8010
```

总控端同样不接受 `0.0.0.0` 裸监听：需要跨主机接入时改为绑定的具体内网地址，并配合防火墙白名单。

边缘设备接入凭据由 `python -m backend.issue_credential` 签发与撤销（令牌只在签发时打印一次），详细流程见 [P0整改完整修改方案.md](P0整改完整修改方案.md) 第 6 节。

边缘端配置中设置 `control_center.enabled=true` 和总控地址后，会连接 `WS /api/edge/ws`。当前总控原型仍使用进程内实时状态和命令记录，尚未接入 Redis/MySQL 持久化。
