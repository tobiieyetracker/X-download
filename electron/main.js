const { app, BrowserWindow, ipcMain, shell } = require("electron");
const { spawn } = require("node:child_process");
const { execFile } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const { promisify } = require("node:util");
const ExifReader = require("exifreader");
const ffprobe = require("ffprobe-static");

const execFileAsync = promisify(execFile);

const projectRoot = path.resolve(__dirname, "..");
const downloaderScript = path.join(projectRoot, "mode_download.py");
const downloadsRoot = path.join(projectRoot, "downloads");

const DEFAULT_SETTINGS = Object.freeze({
  maxFileSizeMb: 1024,
  maxTotalSizeMb: 4096,
  maxFiles: 50,
  cleanupFailedTasks: true
});

let settings = { ...DEFAULT_SETTINGS };

function boundedInteger(value, fallback, minimum, maximum) {
  const number = Number(value);
  if (!Number.isInteger(number)) return fallback;
  return Math.min(maximum, Math.max(minimum, number));
}

function normalizeSettings(value) {
  const raw = value && typeof value === "object" ? value : {};
  return {
    maxFileSizeMb: boundedInteger(raw.maxFileSizeMb, DEFAULT_SETTINGS.maxFileSizeMb, 1, 8192),
    maxTotalSizeMb: boundedInteger(raw.maxTotalSizeMb, DEFAULT_SETTINGS.maxTotalSizeMb, 1, 32768),
    maxFiles: boundedInteger(raw.maxFiles, DEFAULT_SETTINGS.maxFiles, 1, 100),
    cleanupFailedTasks: raw.cleanupFailedTasks !== false
  };
}

function settingsFile() {
  return path.join(app.getPath("userData"), "settings.json");
}

async function loadSettings() {
  try {
    const value = JSON.parse(await fs.readFile(settingsFile(), "utf8"));
    return normalizeSettings(value);
  } catch (error) {
    if (error.code !== "ENOENT") console.warn("无法读取下载设置，将使用默认值。", error.message);
    return { ...DEFAULT_SETTINGS };
  }
}

async function persistSettings(value) {
  settings = normalizeSettings(value);
  await fs.mkdir(app.getPath("userData"), { recursive: true });
  await fs.writeFile(settingsFile(), `${JSON.stringify(settings, null, 2)}\n`, "utf8");
  return settings;
}

function isXPostUrl(value) {
  try {
    const url = new URL(value.trim());
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    return url.protocol === "https:" && (host === "x.com" || host === "twitter.com") && /\/status\/\d+/.test(url.pathname);
  } catch {
    return false;
  }
}

function timestamp() {
  const date = new Date();
  const pad = (value, width = 2) => String(value).padStart(width, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    "T",
    pad(date.getHours()),
    "-",
    pad(date.getMinutes()),
    "-",
    pad(date.getSeconds()),
    "-",
    pad(date.getMilliseconds(), 3)
  ].join("");
}

function mediaFolder(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return path.join(downloadsRoot, `${date.getFullYear()}.${pad(date.getMonth() + 1)}`);
}

function parseMediaDate(value) {
  if (typeof value !== "string") return null;
  const exifMatch = value.match(/^(\d{4})[:.-](\d{2})[:.-](\d{2})/);
  if (exifMatch) {
    const [, year, month, day] = exifMatch;
    const date = new Date(Number(year), Number(month) - 1, Number(day));
    return Number.isNaN(date.valueOf()) ? null : date;
  }
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? null : date;
}

function tagValue(tag) {
  if (!tag) return null;
  if (typeof tag.description === "string") return tag.description;
  if (typeof tag.value === "string") return tag.value;
  if (Array.isArray(tag.value) && typeof tag.value[0] === "string") return tag.value[0];
  return null;
}

async function imageCreationDate(filePath) {
  const tags = await ExifReader.load(filePath);
  for (const name of ["DateTimeOriginal", "CreateDate", "DateTimeDigitized", "ModifyDate"]) {
    const date = parseMediaDate(tagValue(tags[name]));
    if (date) return date;
  }
  return null;
}

async function videoCreationDate(filePath) {
  const { stdout } = await execFileAsync(ffprobe.path, [
    "-v", "error", "-print_format", "json", "-show_format", "-show_streams", filePath
  ], { windowsHide: true, maxBuffer: 1024 * 1024 });
  const probe = JSON.parse(stdout);
  const values = [
    probe.format?.tags?.creation_time,
    ...(probe.streams || []).map((stream) => stream.tags?.creation_time)
  ];
  for (const value of values) {
    const date = parseMediaDate(value);
    if (date) return date;
  }
  return null;
}

async function mediaCreationDate(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  try {
    if ([".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif"].includes(extension)) {
      return await imageCreationDate(filePath);
    }
    if ([".mp4", ".mov", ".m4v", ".webm"].includes(extension)) {
      return await videoCreationDate(filePath);
    }
  } catch {
    // Some services strip metadata or return unsupported formats. Use Unknown instead.
  }
  return null;
}

async function availableDestination(directory, filename) {
  const extension = path.extname(filename);
  const basename = path.basename(filename, extension);
  let candidate = path.join(directory, filename);
  let suffix = 2;
  while (true) {
    try {
      await fs.access(candidate);
      candidate = path.join(directory, `${basename}-${suffix}${extension}`);
      suffix += 1;
    } catch {
      return candidate;
    }
  }
}

async function organizeByMediaDate(taskDirectory, result) {
  const archives = [];
  for (const savedPath of result.saved) {
    const source = path.resolve(savedPath);
    if (!source.startsWith(`${path.resolve(taskDirectory)}${path.sep}`)) {
      throw new Error("下载器返回了无效的文件路径。");
    }
    const date = await mediaCreationDate(source);
    const destinationDirectory = date ? mediaFolder(date) : path.join(downloadsRoot, "未知日期");
    await fs.mkdir(destinationDirectory, { recursive: true });
    const destination = await availableDestination(destinationDirectory, path.basename(source));
    await fs.rename(source, destination);
    archives.push({ file: destination, directory: destinationDirectory, mediaDate: date?.toISOString() || null });
  }
  result.saved = archives.map((item) => item.file);
  await fs.rm(taskDirectory, { recursive: true, force: true });
  return { directories: [...new Set(archives.map((item) => item.directory))], archives };
}

function execute(command, args, onOutput) {
  return new Promise((resolve, reject) => {
    const process = spawn(command, args, { windowsHide: true });
    let output = "";
    let started = false;
    process.stdout.on("data", (chunk) => {
      const text = chunk.toString();
      output += text;
      onOutput(text);
    });
    process.stderr.on("data", (chunk) => {
      const text = chunk.toString();
      output += text;
      onOutput(text);
    });
    process.once("spawn", () => { started = true; });
    process.once("error", (error) => reject(error));
    process.once("close", (code) => {
      if (!started) return;
      if (code === 0) resolve(output);
      else reject(new Error(`下载脚本退出码为 ${code}。\n${output}`));
    });
  });
}

async function runDownloader(postUrl, onLog, onProgress, currentSettings) {
  const taskDirectory = path.join(downloadsRoot, ".staging", timestamp());
  await fs.mkdir(taskDirectory, { recursive: true });
  const args = [
    "-3",
    downloaderScript,
    postUrl,
    "-m",
    "auto",
    "-o",
    taskDirectory,
    "--progress-json",
    "--max-file-mb",
    String(currentSettings.maxFileSizeMb),
    "--max-total-mb",
    String(currentSettings.maxTotalSizeMb),
    "--max-files",
    String(currentSettings.maxFiles)
  ];
  let lineBuffer = "";
  const consumeOutput = (chunk) => {
    lineBuffer += chunk;
    const lines = lineBuffer.split(/\r?\n/);
    lineBuffer = lines.pop();
    for (const line of lines) {
      if (line.startsWith("PROGRESS_JSON:")) {
        try { onProgress(JSON.parse(line.slice("PROGRESS_JSON:".length))); }
        catch { onLog(`${line}\n`); }
      } else if (line) onLog(`${line}\n`);
    }
  };

  try {
    try {
      await execute("py", args, consumeOutput);
    } catch (pyError) {
      onLog("py 启动失败，正在尝试 python…\n");
      await execute("python", args.slice(1), consumeOutput).catch((pythonError) => {
        throw new Error(`无法运行 Python 下载器。\npy: ${pyError.message}\npython: ${pythonError.message}`);
      });
    }
    const resultPath = path.join(taskDirectory, "auto", "result.json");
    const result = JSON.parse(await fs.readFile(resultPath, "utf8"));
    const archive = await organizeByMediaDate(taskDirectory, result);
    return { ...archive, result };
  } catch (error) {
    if (currentSettings.cleanupFailedTasks) {
      await fs.rm(taskDirectory, { recursive: true, force: true }).catch(() => {});
      onLog("已清理失败任务的临时文件。\n");
    }
    throw error;
  }
}

function createWindow() {
  const window = new BrowserWindow({
    width: 860,
    height: 690,
    minWidth: 720,
    minHeight: 560,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });
  window.removeMenu();
  window.loadFile(path.join(__dirname, "index.html"));
}

app.whenReady().then(async () => {
  settings = await loadSettings();
  ipcMain.handle("get-settings", () => settings);
  ipcMain.handle("save-settings", (_event, value) => persistSettings(value));
  ipcMain.handle("download", async (event, postUrl) => {
    if (typeof postUrl !== "string" || !isXPostUrl(postUrl)) {
      throw new Error("请输入有效的 X / Twitter 帖子链接，例如 https://x.com/name/status/123。");
    }
    return runDownloader(
      postUrl.trim(),
      (text) => event.sender.send("download-log", text),
      (progress) => event.sender.send("download-progress", progress),
      settings
    );
  });
  ipcMain.handle("open-download-folder", async (_event, directory) => {
    if (typeof directory !== "string" || !path.resolve(directory).startsWith(`${downloadsRoot}${path.sep}`)) {
      throw new Error("下载目录无效。");
    }
    const error = await shell.openPath(directory);
    if (error) throw new Error(error);
  });
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
