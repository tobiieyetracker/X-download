# X download

X（Twitter）视频 / 图片解析与下载工具。

从第三方快捷指令中抽出可复用流程，去掉配置中心与私人接口，改用公开 API。

## 功能

- 菜单模式：默认（自动）/ 图片 / 单视频 / 多视频 / GIF
- 主接口：`https://dwnld.nichind.dev/`（[download.nichind.dev](https://download.nichind.dev/) 公开 API）
- 备选：`https://savetwitter.net/api/ajaxSearch`
- 选质：图片优先高分辨率；视频只保留最高清一档

## 本地脚本（Windows）

```bash
# 默认自动识别
python mode_download.py "https://x.com/.../status/..." -m auto

# 其它模式
python mode_download.py "链接" -m photo
python mode_download.py "链接" -m single_video
python mode_download.py "链接" -m multi_video
python mode_download.py "链接" -m gif
```

仅最高清下载：

```bash
python best_quality_download.py "链接"
```

## Electron 桌面版（Windows）

桌面版复用同一套 Python 解析与下载逻辑：粘贴 X 帖子链接后会自动识别图片或视频，并下载最高清媒体。

```bash
npm install
npm start
```

- 需要已安装 Python 3；应用会优先使用 Windows 的 `py -3`。
- 下载完成后会读取媒体文件自身的创建日期（照片 EXIF 或视频 `creation_time`），并归档到项目目录下的 `downloads\YYYY.MM`，例如 `downloads\2026.03`。没有保留创建日期的媒体会放入 `downloads\未知日期`，不会用下载时间代替。
- 下载大文件时会显示当前文件的实时字节进度；服务器未提供文件大小时，进度条会显示为持续加载状态。
- 设置面板默认限制单文件 1024 MiB、单次总量 4096 MiB、最多 50 个文件，也可以自行调整；失败任务默认会清理临时文件。
- Electron 设置保存在系统用户目录，不写入项目目录；原始解析响应只在命令行显式使用 `--debug` 时保存。

## iOS 快捷指令（未签名）

未签名包：`dist/X-Download.shortcut`  

iOS 15+ 通常**不能直接导入**未签名文件，需在 **Mac** 上签名后再装到 iPhone。

### 在 Mac 上签名并安装

1. 把 `dist/X-Download.shortcut` 拷到 Mac（需已登录 Apple ID，并装有「快捷指令」）。
2. 在终端执行：

```bash
shortcuts sign \
  --mode anyone \
  --input dist/X-Download.shortcut \
  --output dist/X-Download-signed.shortcut
```

- `--mode anyone`：任何人可添加（自用/分享都方便）
- 仅自己用可改为：`--mode people-who-know-me`

3. 装到 iPhone（任选其一）：
   - 隔空投送 `X-Download-signed.shortcut` 到手机，用「快捷指令」打开
   - 或放到 iCloud，手机上打开
   - 或在 Mac「快捷指令」导入后，分享 → **拷贝 iCloud 链接**，手机用链接获取

4. 注意：
   - 签名只能在 Mac 做，Windows 不行
   - 改过快捷指令逻辑后，需要**重新签名**再导入
   - 若提示找不到 `shortcuts` 命令，确认 macOS /「快捷指令」版本够新

也可不导入文件，按 `MODES.md` / `IPHONE_BUILD.md` 在手机上对照搭建。

## 文档

| 文件 | 说明 |
|------|------|
| `MODES.md` | 菜单模式与接口映射 |
| `QUALITY_RULES.md` | 最高清选质规则 |
| `dist/README.md` | 快捷指令包与 Mac 签名说明 |

## 说明

请仅下载你有权访问、用于个人非商业用途的内容，并遵守当地法律与平台条款。
