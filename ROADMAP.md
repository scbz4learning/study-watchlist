# 后续路径 / Roadmap

> 这一版（v0.2.1）是初赛交付。后续按"复赛 → 技术突破奖 → 长期"的优先级推进。
> 下面三个方向**目前都不在初赛交付里**，是复赛及以后的演进计划。

---

## 方向 A · bilibili 分片选择（playlist / 分P / 合集）

**用户场景**：现在 v0.2.x 一次搜索拿 20 条"整段视频"。如果 UP 主把课拆成 24 个 10 分钟分P、或放在一个 5 章 50 个讲座的合集里——学生目前拿到的还是"整段"，可读性不够。

**做法**：
- v0.2.x 提示词 → 实时分；搜索结果保留
- v0.3 加 **分 P 解析**（一个 bvid 多段）：
  - `https://api.bilibili.com/x/player/pagelist?bvid=<bvid>` → `part[]`，每段带 `duration`（秒）+ `page` 编号 + `from`（秒，父视频里偏移）
  - 拆分后每段的真实 `from..to` 是 cue-level 的天然单位
- v0.3 顺便加 **合集解析**（创作合集）：
  - `https://api.bilibili.com/x/polymer/web-space/home_season_arcs?mid=<mid>` → `arcs[].archives[]`
- UI：在实时结果列表的每条上加一个「展开分P」按钮；点开后每段一行、字号、复选框
- 助手：把 `playlist-from` 与 `playlist-to` 字段加进 source schema（同 L0 卡那样扩 `sys.video` 不现实——这是 Splash 自己实现的字段，不靠 sys.*，合规）

**价格**（少读）：
- snapshot 生成从 30s 升到 1–3 min（多次 pagelist 调用，需串行 + sleep + 限流重试）
- UI 需要全新分P抽屉，复杂度 +1

**比赛合规**：✅
- 数据仍是 bilibili 公开 API（已在 `manifest.network.hosts`）
- 不编 id、不写"为什么选这段"
- 重点关注“no-facts”：分P 的 from/to/duration/page 都是来源字段，不误

---

## 方向 B · AI 字幕 cue-level 切割

**用户场景**：理想是——预算 60 分钟，输出 "合集1 第2集 第2-10 分钟 + 合集2 第5集 第20-30 分钟 + ..."。粒度级别的。

**做法**（分两个阶段）：

### B1 · 字幕可的结构化（10/09 前基建）
- bilibili `https://api.bilibili.com/x/player/wbi/v2?bvid=<bvid>&cid=<cid>` 返回 `subtitle.subtitles[]`，每条带 `subtitle_url`（一个 JSON，含 `[{from:秒, to:秒, content:文本}]` cues）
- 在 Splah 中：按 `from`/`to` 加上 cue 列表算出"跨视频拼切"
- "为什么选这条 cue"：**不靠模型**也能出——只用关键词搜索选个**匹配主题中某个关键词的 top-N cues**，再按预算求最切贴部分
- 重点：**场景缺失是高频的**——必须用"该视频无字幕，回退到整段时长"这种可见路径，**不能假装"AI 已分析"**

### B2 · 模型选 cue（技术突破）
- 调宿主 `model.complete(prompt)` —— prompt = `主题 + 候选 cue 列表（每个带 from/to/text）+ 预算（秒）`；模型返回 = `选中的 id 列表 + "为什么"的原因`
- 不在 bundle 里带 key —— 调模型时宿主从它自己的 AI Providers sheet 取（**官方 no-secrets 硬规则**）
- **no-facts 边界是设计重点**：所有 AI 输出必须明确标 "AI 建议"，不写成"为你定制"

**价格**：
- B1 是基建：字幕 fetch + parse + cue-level 算术 + UI（估计 8-16 小时）
- B2 是 model 集成：prompt 设计、失败/超时/空结果处理、调用前后对照实验素材（估计 8-12 小时）

**比赛合规**：
- ✅ 数据本身（字幕）是来源事实
- ⚠️ **“为什么选这条 cue” 是 AI 输出** —— 必须标注 "AI 建议"，不能写成事实
- 重点关注：card-host 不服务 `model`/`octos.*`，**初赛环境里 AI 调不出来**。这是初赛不加 B1/B2 的硬约束。

---

## 方向 C · MIT OpenCourseWare 课程结构源（长期）
- OCW `/courses/<slug>/data.json` + `/pages/lecture-notes/` + `/video_galleries/lecture-videos/` 都是免 key 免 token
- URL：`https://ocw.mit.edu/courses/<we-pages>/<lecture-N-slug>/`拿真实视频 id；时长按 YouTube watch page 拿（复用 make_snapshot.py 的解析器）
- 价值：提前先定课程大纲，再拍视频（未提交课程里的 "备考 "场景的可控推荐）
- 初赛未做：复赛不一定做（增加复杂度，需另跳一次）

---

## 阶段优先级

| 时间 | 动作 | 计划 |
|---|---|---|
| 10/06 23:59 | 初赛交付完成（v0.2.1） | ✅ |
| 10/07–10/09 | 方向 A（分P/合集）与 B1（字幕基建） | 复赛交付项 |
| 10/09 23:59 | 复赛交付 + 方向 B2（模型选 cue）取证据 | 最佳 Agentic 赛项 |
| 10/10–10/11 | 跨复赛交付 + AI 选 cue + 复盘 | 技术突破赛项证据 |
| 10/12 | 复赛答辩 | 以复赛交付 + 技术突破证据作仓 |
| 长期 | 方向 C（OCW 课程源） | “备考套件” 里不再藏板 |

---

## 与初赛交付的关系

- **v0.2.1 完整**（初赛交付，不动）
- 上面三个方向均不依赖复赛交付，互相独立
- 10/09 复赛交付：v0.2.1 + **A (分P) + B1 (字幕 cue)** + AI 选 cue 作为 “最佳 Agentic” 重头
- 技术突破仅在合赛：方向 A/B2 上会的"延迟/成本/质量前后对照" 详细说明

---

## 已验证的库 （参考资料，memos 下同）

- bilibili v2 搜索：免 key、免 cookie；本机 3s 返 20 条 ✅
- bilibili pagelist：免 key、返 part + duration(秒) + from(秒) ✅
- bilibili subtitle：免 key、cue JSON 里面是 `[from,to,content]`；超过 3 个关键词可能出现限流 ⚠️
- MIT OCW HTML：免 key、静态拉取 ✅
- OCW `data.json`：免 key、结构元信息，但**不含讲座清单** ✅
- bilibili 合集 (arc)：免 key、arcs 结构 list、每个 arc 里含独立 videos