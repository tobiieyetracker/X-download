# X-Download.shortcut（未签名）

建议显示名：X下载·自用

## 文件

| 文件 | 说明 |
|------|------|
| `X-Download.shortcut` | 未签名快捷指令 |
| `X-Download.plist` / `X-Download.json` | 可读副本 |

## 流程

分享链接 → 选模式（默认 / 图片 / 单视频 / 多视频 / GIF）→ POST nichind → 按类型下载 → 存相册

主接口：`https://dwnld.nichind.dev/`

## 在 Mac 上签名并装到 iPhone

iOS 15+ 通常无法直接导入未签名 `.shortcut`，需在 Mac 签名。

### 1. 准备

- 将本目录的 `X-Download.shortcut` 拷到 Mac
- Mac 已登录 Apple ID，并装有「快捷指令」App

### 2. 签名

在仓库根目录或本文件所在路径执行：

```bash
shortcuts sign \
  --mode anyone \
  --input dist/X-Download.shortcut \
  --output dist/X-Download-signed.shortcut
```

| 参数 | 含义 |
|------|------|
| `--mode anyone` | 任何人可添加（自用/分享） |
| `--mode people-who-know-me` | 仅联系人可添加 |

### 3. 安装到 iPhone

任选其一：

- **隔空投送** `X-Download-signed.shortcut` → 手机用「快捷指令」打开
- 放到 **iCloud**，手机打开该文件
- Mac「快捷指令」导入后 → 分享 → **拷贝 iCloud 链接** → 手机打开链接获取

### 4. 注意

- 签名只能在 **Mac** 完成，Windows 不行
- 修改快捷指令后需 **重新签名** 再导入
- 找不到 `shortcuts` 命令时，检查 macOS /「快捷指令」是否够新

也可按仓库内 `MODES.md`、`IPHONE_BUILD.md` 在 iPhone 上手工搭建。
