# 菜单模式设计（对齐原版分流原因）

原版弹出菜单，是因为**不同类型适合不同处理方式**。
我们同样做菜单，并加 **默认 = 自动识别**。

## 菜单项

| 菜单 | mode | 主接口 | 行为 |
|------|------|--------|------|
| 图片 | `photo` | `nichind` → 备选 `ajaxSearch` | 只下照片，最高清 |
| GIF | `gif` | `ajaxSearch` | 只下 GIF/`tweet_video`，最高清 |
| 单视频 | `single_video` | `nichind` → 备选 `ajaxSearch` | 只下 1 个最高清视频 |
| 多视频 | `multi_video` | `nichind` → 备选 `ajaxSearch` | 每个视频各留最高清一档 |
| 默认 | `auto` | `nichind` → 备选 `ajaxSearch` | 自动识别图+视频，全部最高清 |

## 公开接口（写死）

| 用途 | 地址 | 说明 |
|------|------|------|
| 主解析 | `https://dwnld.nichind.dev/` | [download.nichind.dev](https://download.nichind.dev/) 的公开 API |
| 备选 / GIF | `https://savetwitter.net/api/ajaxSearch` | 原配置 `pic-gif`，公开站点 |

请求 nichind 示例：`POST JSON {"url":"<帖子链接>"}`，返回 `picker` 列表。

## 明确不用

| 地址 | 原因 |
|------|------|
| `https://fenguox.fenguo.icu/?url=` | 疯果私人域名 |
| 疯果配置中心 JSON | 远程控制使用者 |
| `duox` / `duo2x` | 需作者快捷指令鉴权 |

## 为什么还要菜单

- **单视频**：只要 1 条最高清，不多下  
- **图片**：不误下视频轨/封面  
- **多视频**：按「每条视频」分别保最高清  
- **GIF**：和普通视频分开筛  
- **默认**：混合帖一次拿齐  

## 命令

```bash
python mode_download.py "帖子链接" -m auto
python mode_download.py "帖子链接" -m photo
python mode_download.py "帖子链接" -m single_video
python mode_download.py "帖子链接" -m multi_video
python mode_download.py "帖子链接" -m gif
```
