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

## iOS 快捷指令（未签名）

`dist/X-Download.shortcut` 为未签名包。iOS 15+ 通常需 Mac 签名后再导入：

```bash
shortcuts sign --mode anyone --input dist/X-Download.shortcut --output dist/X-Download-signed.shortcut
```

或按 `MODES.md` / `IPHONE_BUILD.md` 在手机上对照搭建。

## 文档

| 文件 | 说明 |
|------|------|
| `MODES.md` | 菜单模式与接口映射 |
| `QUALITY_RULES.md` | 最高清选质规则 |
| `PATTERN.md` | 原版流程模式分析 |
| `dist/README.md` | 快捷指令包说明 |

## 说明

请仅下载你有权访问、用于个人非商业用途的内容，并遵守当地法律与平台条款。
