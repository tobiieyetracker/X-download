const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("xDownload", {
  download: (url) => ipcRenderer.invoke("download", url),
  openFolder: (directory) => ipcRenderer.invoke("open-download-folder", directory),
  onLog: (callback) => ipcRenderer.on("download-log", (_event, text) => callback(text)),
  onProgress: (callback) => ipcRenderer.on("download-progress", (_event, progress) => callback(progress))
});
