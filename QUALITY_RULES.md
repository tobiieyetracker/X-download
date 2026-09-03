# 最高清选质规则

解析固定走：`POST https://savetwitter.net/api/ajaxSearch`  
（`q=帖子链接`，`lang=en`）—— **无配置中心、无广告**。

## 图片

1. 只保留 `pbs.twimg.com/media/...`
2. **丢掉** `amplify_video_thumb` / `ext_tw_video_thumb`（视频封面）
3. 下载地址统一：`...jpg?name=orig`（原图）
4. 同一 `media_id` 只下一份

## 视频

1. 收集所有 `video.twimg.com/.../*.mp4`
2. 从路径 `/1920x1080/` 这类片段读宽高
3. 按 **宽×高** 排序，**只保留最大的一档**
4. 720p / 360p 等同片低清全部丢弃

## 下载顺序

1. 优先直连 twimg  
2. 失败再用 `dl.snapcdn.app/get?token=...` 代理  

## 脚本

```bash
python best_quality_download.py "https://x.com/<user>/status/<post_id>"
```

输出目录默认：`downloads/best/`，并写 `result.json`（只含媒体解析结果和最终选中项，不保存代理 token）。原始解析响应仅在显式使用 `--debug` 时写入 `ajaxSearch_data.html`。
