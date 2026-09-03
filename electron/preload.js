const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("xDownload", {
  download: (url) => ipcRenderer.invoke("download", url),
  openFolder: (directory) => ipcRenderer.invoke("open-download-folder", directory),
  getSettings: () => ipcRenderer.invoke("get-settings"),
  saveSettings: (settings) => ipcRenderer.invoke("save-settings", settings),
  onLog: (callback) => ipcRenderer.on("download-log", (_event, text) => callback(text)),
  onProgress: (callback) => ipcRenderer.on("download-progress", (_event, progress) => callback(progress))
});
