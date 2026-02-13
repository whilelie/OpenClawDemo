# YouTube 频道视频抓取方案

## 问题
当前环境下 YouTube 抓取受限：
- yt-dlp 需要 JS 运行时
- Web 搜索需要 Brave API
- Browser 工具需要 Chrome 扩展

## 可行方案

### 方案 1: 配置 Brave Search API（推荐）
1. 获取 Brave Search API key: https://api.search.brave.com/
2. 配置: `openclaw configure --section web`
3. 使用搜索查询: `site:youtube.com/@fangzhuan` + 日期

### 方案 2: 使用 YouTube Data API v3
1. 申请 API key: https://developers.google.com/youtube/v3
2. 调用 API 获取频道视频列表
3. Cron Job 调用 API 而非直接抓取

### 方案 3: 外部 RSS 服务
使用第三方服务如 RSSHub 转换 YouTube 为 RSS:
- https://rsshub.app/youtube/channel/:channelId
- 但需要先获取 channel ID

### 方案 4: 本地配置 JavaScript 运行时
安装 deno 或 nodejs，让 yt-dlp 正常工作:
```bash
# 安装 deno
curl -fsSL https://deno.land/install.sh | sh
```

## 建议
方案 1 最简单，申请 Brave API key 免费且快速。

---
频道: www.youtube.com/@fangzhuan (方的言)
