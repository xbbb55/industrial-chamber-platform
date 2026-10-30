# Windows 便携样本构建

样本目标为 Windows 10/11 x64，包含 Electron 外壳、Vue 生产构建和冻结后的 `device_edge` onedir 后端。MySQL 服务和 C++ 共享内存应用层由现场环境提供，不包含在压缩包中。

## 构建

在项目根目录执行：

```powershell
python -m pip install -r device_edge/requirements.txt
python -m pip install -r packaging/requirements-build.txt
npm install
npm run package:portable
```

产物：

```text
artifacts/Industrial-Chamber-Platform-win-x64-portable.zip
```

## 运行前准备

1. 解压 ZIP 后双击 `Industrial Chamber Platform.exe`。
2. 首次启动会在 Electron 用户数据目录生成 `device-edge.config.json`；按现场设备修改共享内存名称、数据库地址和端口。
3. 通过系统环境变量提供 `MYSQL_PWD`，或按现有部署规范注入配置指定的密码环境变量。
4. 先启动 C++ 应用层，使 `BE_W` 和 `BE_R` 共享内存可用；`FE_W` 由 `device_edge` 创建。

Electron 只监听 `127.0.0.1`，窗口关闭时会停止本地 `device_edge` 子进程。日志写入 Electron 用户数据目录下的 `logs` 文件夹。

## 部署版本与 profile

两个交付物对应两个部署版本，profile 由交付物固定，不交给现场临场切换：

| 交付物 | 版本 | `DEPLOYMENT_PROFILE` | 监听地址 | Cookie 模式 |
| --- | --- | --- | --- | --- |
| Electron 便携包 | 本机版 | `local` | `127.0.0.1` | `secure` |
| 独立边缘服务包 | 多设备版 | `multi-device` | 具体网卡地址 | 无 HTTPS 时 `strict-http`（需书面风险接受）；有 HTTPS 反代时 `secure` + `TRUSTED_PROXY_IPS` |

服务启动时会执行部署自检，监听地址与 Cookie 模式不自洽时**拒绝启动**；任何形态都不接受 `0.0.0.0` 裸监听。
