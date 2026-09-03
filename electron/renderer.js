const form = document.querySelector("#download-form");
const urlInput = document.querySelector("#post-url");
const submitButton = document.querySelector("#download-button");
const status = document.querySelector("#status");
const log = document.querySelector("#log");
const result = document.querySelector("#result");
const progressPanel = document.querySelector("#progress-panel");
const progressBar = document.querySelector("#progress-bar");
const progressLabel = document.querySelector("#progress-label");
const maxFileSizeInput = document.querySelector("#max-file-size");
const maxTotalSizeInput = document.querySelector("#max-total-size");
const maxFilesInput = document.querySelector("#max-files");
const cleanupFailedTasksInput = document.querySelector("#cleanup-failed-tasks");
const saveSettingsButton = document.querySelector("#save-settings");
const settingsStatus = document.querySelector("#settings-status");

function setBusy(busy) {
  submitButton.disabled = busy;
  submitButton.textContent = busy ? "正在解析并下载…" : "识别并下载";
}

function addLog(text) {
  log.textContent += text;
  log.scrollTop = log.scrollHeight;
}

function showResult(data) {
  const { directories, result: download } = data;
  const media = [
    ...download.photos.map(() => "图片"),
    ...download.videos.map((video) => `视频${video.width && video.height ? ` ${video.width}×${video.height}` : ""}`)
  ];
  result.replaceChildren();
  const summary = document.createElement("p");
  summary.textContent = `已保存 ${download.saved.length} 个文件：${media.join("、") || "未发现媒体"}`;
  const location = document.createElement("p");
  location.className = "location";
  location.textContent = directories.join("\n");
  result.append(summary, location);
  for (const directory of directories) {
    const openButton = document.createElement("button");
    openButton.className = "secondary";
    openButton.textContent = `打开 ${directory.split("\\").pop()} 文件夹`;
    openButton.addEventListener("click", () => window.xDownload.openFolder(directory));
    result.append(openButton);
  }
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderSettings(settings) {
  maxFileSizeInput.value = settings.maxFileSizeMb;
  maxTotalSizeInput.value = settings.maxTotalSizeMb;
  maxFilesInput.value = settings.maxFiles;
  cleanupFailedTasksInput.checked = settings.cleanupFailedTasks;
}

async function loadSettings() {
  try {
    renderSettings(await window.xDownload.getSettings());
  } catch (error) {
    settingsStatus.textContent = error.message || "设置读取失败";
  }
}

saveSettingsButton.addEventListener("click", async () => {
  settingsStatus.textContent = "正在保存…";
  try {
    const settings = await window.xDownload.saveSettings({
      maxFileSizeMb: Number(maxFileSizeInput.value),
      maxTotalSizeMb: Number(maxTotalSizeInput.value),
      maxFiles: Number(maxFilesInput.value),
      cleanupFailedTasks: cleanupFailedTasksInput.checked
    });
    renderSettings(settings);
    settingsStatus.textContent = "已保存";
  } catch (error) {
    settingsStatus.textContent = error.message || "设置保存失败";
  }
});

loadSettings();

window.xDownload.onProgress((progress) => {
  progressPanel.hidden = false;
  if (progress.type === "queue" && progress.total_files === 0) {
    progressBar.value = 0;
    progressLabel.textContent = "没有可下载的媒体";
    return;
  }
  if (progress.type === "file-start") {
    progressBar.removeAttribute("value");
    progressLabel.textContent = `正在下载第 ${progress.index}/${progress.total_files} 个文件：${progress.name}`;
  }
  if (progress.type === "bytes") {
    if (progress.total) {
      progressBar.max = 100;
      progressBar.value = (progress.downloaded / progress.total) * 100;
      progressLabel.textContent = `正在下载第 ${progress.index}/${progress.total_files} 个文件：${progress.name}（${formatBytes(progress.downloaded)} / ${formatBytes(progress.total)}）`;
    } else {
      progressBar.removeAttribute("value");
      progressLabel.textContent = `正在下载第 ${progress.index}/${progress.total_files} 个文件：${progress.name}（${formatBytes(progress.downloaded)}）`;
    }
  }
  if (progress.type === "file-complete") {
    progressBar.value = 100;
    progressLabel.textContent = `已完成第 ${progress.index}/${progress.total_files} 个文件：${progress.name}`;
  }
});

window.xDownload.onLog(addLog);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  log.textContent = "";
  result.replaceChildren();
  progressPanel.hidden = true;
  progressBar.value = 0;
  status.textContent = "正在连接公开解析服务…";
  status.className = "working";
  setBusy(true);
  try {
    const data = await window.xDownload.download(urlInput.value);
    status.textContent = "下载完成";
    status.className = "success";
    showResult(data);
    progressPanel.hidden = true;
  } catch (error) {
    status.textContent = error.message || "下载失败";
    status.className = "error";
  } finally {
    setBusy(false);
  }
});
