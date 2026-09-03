const form = document.querySelector("#download-form");
const urlInput = document.querySelector("#post-url");
const submitButton = document.querySelector("#download-button");
const status = document.querySelector("#status");
const log = document.querySelector("#log");
const result = document.querySelector("#result");
const progressPanel = document.querySelector("#progress-panel");
const progressBar = document.querySelector("#progress-bar");
const progressLabel = document.querySelector("#progress-label");
const progressPercent = document.querySelector("#progress-percent");
const clearUrlButton = document.querySelector("#clear-url");
const maxFileSizeInput = document.querySelector("#max-file-size");
const maxTotalSizeInput = document.querySelector("#max-total-size");
const maxFilesInput = document.querySelector("#max-files");
const cleanupFailedTasksInput = document.querySelector("#cleanup-failed-tasks");
const saveSettingsButton = document.querySelector("#save-settings");
const settingsStatus = document.querySelector("#settings-status");

function setBusy(busy) {
  submitButton.disabled = busy;
  submitButton.querySelector("span").textContent = busy ? "正在解析并下载…" : "识别并下载";
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
  const heading = document.createElement("div");
  heading.className = "result-heading";
  const summary = document.createElement("p");
  summary.className = "result-title";
  summary.textContent = media.join("、") || "未发现媒体";
  const count = document.createElement("span");
  count.className = "result-count";
  count.textContent = `${download.saved.length} 个文件`;
  heading.append(summary, count);
  const location = document.createElement("p");
  location.className = "result-location";
  location.textContent = directories.join("\n");
  const actions = document.createElement("div");
  actions.className = "result-actions";
  for (const directory of directories) {
    const openButton = document.createElement("button");
    openButton.className = "secondary";
    openButton.textContent = `打开 ${directory.split("\\").pop()} 文件夹`;
    openButton.addEventListener("click", () => window.xDownload.openFolder(directory));
    actions.append(openButton);
  }
  result.append(heading);
  if (directories.length) result.append(location, actions);
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
    progressPercent.textContent = "0%";
    progressLabel.textContent = "没有可下载的媒体";
    return;
  }
  if (progress.type === "queue") {
    progressPercent.textContent = "0%";
    progressLabel.textContent = `已找到 ${progress.total_files} 个媒体文件`;
  }
  if (progress.type === "file-start") {
    progressBar.removeAttribute("value");
    progressPercent.textContent = "处理中";
    progressLabel.textContent = `正在下载第 ${progress.index}/${progress.total_files} 个文件：${progress.name}`;
  }
  if (progress.type === "bytes") {
    if (progress.total) {
      progressBar.max = 100;
      const percentage = Math.min(100, Math.round((progress.downloaded / progress.total) * 100));
      progressBar.value = percentage;
      progressPercent.textContent = `${percentage}%`;
      progressLabel.textContent = `正在下载第 ${progress.index}/${progress.total_files} 个文件：${progress.name}（${formatBytes(progress.downloaded)} / ${formatBytes(progress.total)}）`;
    } else {
      progressBar.removeAttribute("value");
      progressPercent.textContent = "处理中";
      progressLabel.textContent = `正在下载第 ${progress.index}/${progress.total_files} 个文件：${progress.name}（${formatBytes(progress.downloaded)}）`;
    }
  }
  if (progress.type === "file-complete") {
    progressBar.value = 100;
    progressPercent.textContent = "100%";
    progressLabel.textContent = `已完成第 ${progress.index}/${progress.total_files} 个文件：${progress.name}`;
  }
});

window.xDownload.onLog(addLog);

clearUrlButton.addEventListener("click", () => {
  urlInput.value = "";
  urlInput.focus();
  status.textContent = "等待粘贴一个帖子链接";
  status.className = "";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  log.textContent = "";
  result.replaceChildren();
  progressPanel.hidden = true;
  progressBar.value = 0;
  progressPercent.textContent = "0%";
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
