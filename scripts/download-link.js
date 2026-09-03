const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const path = require("node:path");
const { organizeByMediaDate } = require("../electron/media-archive");

const postUrl = process.argv[2];
const projectRoot = path.resolve(__dirname, "..");
const downloadsRoot = path.join(projectRoot, "downloads");

function isXPostUrl(value) {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase().replace(/^www\./, "");
    return url.protocol === "https:" && ["x.com", "twitter.com"].includes(host) && /\/status\/\d+/.test(url.pathname);
  } catch { return false; }
}

function timestamp() {
  return new Date().toISOString().replaceAll(":", "-").replaceAll(".", "-");
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { windowsHide: true, stdio: "inherit" });
    child.once("error", reject);
    child.once("close", (code) => code === 0 ? resolve() : reject(new Error(`下载器退出码：${code}`)));
  });
}

async function main() {
  if (!isXPostUrl(postUrl)) throw new Error("请提供有效的 X/Twitter 帖子链接。");
  const taskDirectory = path.join(downloadsRoot, ".staging", timestamp());
  let succeeded = false;
  try {
    await fs.mkdir(taskDirectory, { recursive: true });
    await run("py", ["-3", "mode_download.py", postUrl, "-m", "auto", "-o", taskDirectory]);
    const resultPath = path.join(taskDirectory, "auto", "result.json");
    const result = JSON.parse(await fs.readFile(resultPath, "utf8"));
    const archive = await organizeByMediaDate(taskDirectory, result, downloadsRoot);
    succeeded = true;
    console.log(JSON.stringify({ ...archive, result }, null, 2));
  } finally {
    if (!succeeded) await fs.rm(taskDirectory, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; });
