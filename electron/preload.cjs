const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopWindow", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  enterFullscreen: () => ipcRenderer.invoke("window:enter-fullscreen"),
  restoreWindow: () => ipcRenderer.invoke("window:restore"),
  isFullscreen: () => ipcRenderer.invoke("window:is-fullscreen"),
  onFullscreenChange: (callback) => {
    const listener = (_event, isFullscreen) => callback(isFullscreen);
    ipcRenderer.on("window:fullscreen-changed", listener);
    return () => ipcRenderer.removeListener("window:fullscreen-changed", listener);
  },
  close: () => ipcRenderer.invoke("window:close"),
});
