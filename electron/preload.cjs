const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopWindow", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  toggleFullscreen: () => ipcRenderer.invoke("window:toggle-fullscreen"),
  close: () => ipcRenderer.invoke("window:close"),
});
