const { app, BrowserWindow, dialog, session } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const HOST = "127.0.0.1";
const PORT = Number(process.env.INDUSTRIAL_EDGE_PORT || 8765);
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

function startBackend(configPath) {
  const logDir = runtimePath("logs");
  fs.mkdirSync(logDir, { recursive: true });
  const stdout = fs.openSync(path.join(logDir, "device-edge.log"), "a");
  const stderr = fs.openSync(path.join(logDir, "device-edge.error.log"), "a");
  const executable = app.isPackaged
    ? resourcePath("device_edge", "device_edge.exe")
    : path.join(__dirname, "..", ".venv310", "Scripts", "python.exe");
  const args = app.isPackaged
    ? ["serve", "--config", configPath, "--host", HOST, "--port", String(PORT)]
    : ["-m", "device_edge.run_edge", "serve", "--config", configPath, "--host", HOST, "--port", String(PORT)];
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

async function waitForBackend() {
  // P0-1: /api/status is no longer the launcher probe; /healthz is anonymous
  // and returns {"ok": true} without exposing device or config details.
  const endpoint = `http://${HOST}:${PORT}/healthz`;
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
  const configPath = ensureRuntimeFiles();
  startBackend(configPath);
  await waitForBackend();
  session.defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 720,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.once("ready-to-show", () => mainWindow.show());
  await mainWindow.loadURL(`http://${HOST}:${PORT}/`);
}

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
