const { execFile } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const { promisify } = require("node:util");
const ExifReader = require("exifreader");
const ffprobe = require("ffprobe-static");

const execFileAsync = promisify(execFile);

function parseMediaDate(value) {
  if (typeof value !== "string") return null;
  const match = value.match(/^(\d{4})[:.-](\d{2})[:.-](\d{2})/);
  if (match) {
    const [, year, month, day] = match;
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

async function mediaCreationDate(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  try {
    if ([".jpg", ".jpeg", ".png", ".webp", ".heic", ".avif"].includes(extension)) {
      const tags = await ExifReader.load(filePath);
      for (const name of ["DateTimeOriginal", "CreateDate", "DateTimeDigitized", "ModifyDate"]) {
        const date = parseMediaDate(tagValue(tags[name]));
        if (date) return date;
      }
    }
    if ([".mp4", ".mov", ".m4v", ".webm"].includes(extension)) {
      const { stdout } = await execFileAsync(ffprobe.path, [
        "-v", "error", "-print_format", "json", "-show_format", "-show_streams", filePath
      ], { windowsHide: true, maxBuffer: 1024 * 1024 });
      const probe = JSON.parse(stdout);
      const values = [probe.format?.tags?.creation_time, ...(probe.streams || []).map((stream) => stream.tags?.creation_time)];
      for (const value of values) {
        const date = parseMediaDate(value);
        if (date) return date;
      }
    }
  } catch {
    // A source can omit or strip metadata. The caller will use Unknown instead.
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

function mediaFolder(downloadsRoot, date) {
  return path.join(downloadsRoot, `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, "0")}`);
}

async function organizeByMediaDate(taskDirectory, result, downloadsRoot) {
  const root = path.resolve(downloadsRoot);
  const taskRoot = path.resolve(taskDirectory);
  const archives = [];
  for (const savedPath of result.saved) {
    const source = path.resolve(savedPath);
    if (!source.startsWith(`${taskRoot}${path.sep}`)) throw new Error("下载器返回了无效的文件路径。");
    const date = await mediaCreationDate(source);
    const directory = date ? mediaFolder(root, date) : path.join(root, "未知日期");
    await fs.mkdir(directory, { recursive: true });
    const destination = await availableDestination(directory, path.basename(source));
    await fs.rename(source, destination);
    archives.push({ file: destination, directory, mediaDate: date?.toISOString() || null });
  }
  result.saved = archives.map((item) => item.file);
  await fs.rm(taskRoot, { recursive: true, force: true });
  return { directories: [...new Set(archives.map((item) => item.directory))], archives };
}

module.exports = { organizeByMediaDate };
