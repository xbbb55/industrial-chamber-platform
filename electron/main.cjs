const { app, BrowserWindow, dialog, ipcMain, session } = require("electron");
const { spawn } = require("child_process");
const net = require("net");
const fs = require("fs");
const path = require("path");

const HOST = "127.0.0.1";
const REQUESTED_PORT = Number(process.env.INDUSTRIAL_EDGE_PORT || 0);
const DESKTOP_WINDOW_CSS = `
  html, body, #app {
    width: 100%;
    height: 100%;
    min-height: 0;
    overflow: hidden;
    background: transparent !important;
  }
  #app { border-radius: 20px; overflow: hidden; }
  .app-shell:has(.sidebar) .topbar,
  .login-page .login-aside { -webkit-app-region: drag; }
  .app-shell:has(.sidebar) .topbar :is(button, a, input, [role="button"]),
  .login-page .login-panel,
  .window-controls { -webkit-app-region: no-drag; }
  .content { scrollbar-width: none; -ms-overflow-style: none; }
  .content::-webkit-scrollbar { display: none; width: 0; height: 0; }
`;
let backend = null;
let mainWindow = null;

function resourcePath(...parts) {
  return path.join(app.isPackaged ? process.resourcesPath : path.resolve(__dirname, ".."), ...parts);
}

function runtimePath(...parts) {
  return path.join(app.getPath("userData"), ...parts);
}

function ensureRuntimeFiles() {
  fs.mkdirSync(app.getPath("userData"), { recursive: true });
  const configPath = runtimePath("device-edge.config.json");
  if (!fs.existsSync(configPath)) {
    fs.copyFileSync(resourcePath("device-edge.config.sample.json"), configPath);
  }
  return configPath;
}

function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(REQUESTED_PORT, HOST, () => {
      const { port } = server.address();
      server.close((error) => error ? reject(error) : resolve(port));
    });
  });
}

function startBackend(configPath, port) {
  const logDir = runtimePath("logs");
  fs.mkdirSync(logDir, { recursive: true });
  const stdout = fs.openSync(path.join(logDir, "device-edge.log"), "a");
  const stderr = fs.openSync(path.join(logDir, "device-edge.error.log"), "a");
  const executable = app.isPackaged
    ? resourcePath("device_edge", "device_edge.exe")
    : path.join(__dirname, "..", ".venv310", "Scripts", "python.exe");
  const args = app.isPackaged
    ? ["serve", "--config", configPath, "--host", HOST, "--port", String(port)]
    : ["-m", "device_edge.run_edge", "serve", "--config", configPath, "--host", HOST, "--port", String(port)];
  backend = spawn(executable, args, {
    cwd: app.getPath("userData"),
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", stdout, stderr],
    windowsHide: true,
  });
  backend.once("error", (error) => {
    dialog.showErrorBox("后端启动失败", `${error.message}\n\n请查看日志：${logDir}`);
    app.quit();
  });
  backend.once("exit", (code, signal) => {
    if (!app.isQuitting && code !== 0) {
      dialog.showErrorBox("后端已退出", `device_edge 退出码：${code ?? "未知"}，信号：${signal ?? "未知"}\n\n请查看日志：${logDir}`);
      app.quit();
    }
  });
}

async function waitForBackend(port) {
  // P0-1: /api/status is no longer the launcher probe; /healthz is anonymous
  // and returns {"ok": true} without exposing device or config details.
  const endpoint = `http://${HOST}:${port}/healthz`;
  let lastError = "未知错误";
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      if (response.ok) return;
      lastError = `HTTP ${response.status}`;
    } catch (error) {
      lastError = error.message;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`本机后端未在规定时间内就绪：${lastError}`);
}

async function createWindow() {
  const port = await findAvailablePort();
  const configPath = ensureRuntimeFiles();
  startBackend(configPath, port);
  await waitForBackend(port);
  session.defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  const readyToShow = new Promise((resolve) => mainWindow.once("ready-to-show", resolve));
  await mainWindow.loadURL(`http://${HOST}:${port}/`);
  await mainWindow.webContents.insertCSS(DESKTOP_WINDOW_CSS);
  await readyToShow;
  mainWindow.show();
}

ipcMain.handle("window:minimize", (event) => {
  BrowserWindow.fromWebContents(event.sender)?.minimize();
});
ipcMain.handle("window:toggle-fullscreen", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (window) window.setFullScreen(!window.isFullScreen());
});
ipcMain.handle("window:close", (event) => {
  BrowserWindow.fromWebContents(event.sender)?.close();
});

function stopBackend() {
  if (!backend || backend.killed) return;
  backend.kill();
  backend = null;
}

app.whenReady().then(async () => {
  try {
    await createWindow();
  } catch (error) {
    dialog.showErrorBox("工业试验箱平台启动失败", error.message);
    stopBackend();
    app.quit();
  }
});

app.on("before-quit", stopBackend);
app.on("window-all-closed", () => app.quit());
