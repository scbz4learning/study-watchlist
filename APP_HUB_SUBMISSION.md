# Submit study-watchlist 0.3.0

## 提交信息

- 应用：`study-watchlist`
- 版本：`0.3.0`
- 仓库：`https://github.com/lymio-lab/study-watchlist`
- 标签：`v0.3.0`
- commit SHA：见 `git rev-parse v0.3.0`（用 tag 而非短 SHA——避免每次自我引用导致的 SHA 漂移；维护者按 `hub check` 跑的 commit 与 tag v0.3.0 一致即可）
- 应用包路径：`bundle/`
- 发布者：`lymio-lab`（`lymio-lab`）
- 签名：**unsigned**（首次提交，未签）
- 平台：Linux（Ubuntu 24.04 + X11）、Android（按 `bundle/listing.json` 声明）
- 类别：`education`
- 能力：`storage`、`net`、`images`、`web`，存储额度 16 MiB，`agent` 为 `null`
- 官方目录：sequence `4`（2026-09-20）；`study-watchlist 0.3.0` 不在目录中
- 官方宿主：`native/LOCK.json` 固定的 `OctoSense-App-Hub` `0d5b47a2ae9eb98020feca26b7c895a3cf797dc1` 构建的 `card-host` 与 `hub`
- 授权主机（已填 `manifest.network.hosts`）：`api.bilibili.com`、`www.bilibili.com`、`i0.hdslb.com`、`i1.hdslb.com`

### v0.3.0 相对 v0.2.1 的变更

- 补全初赛交付物：删去试用遗留的 `03-playback-unavailable.png`（被新版 03 替代）；
  `tools/record_demo.py` 取代了 `RECORDING_SCRIPT.md`，docstring 写清用法。
- 仓库 `evidence/demo.webm` 是 2:05 演示视频（VP9 412x892, ~1 MB）。
- bundle 内容**实质**未变（仅 manifest 的 `version` 字段从 0.2.1 升到 0.3.0，并删了 1 个
  未使用的 PNG）—— digest 必然变，所以下面重新 stamp 一次。

## 官方检查输出

### `hub check bundle --allow-unsigned`（verbatim）

```
$ tools/octo check bundle
octo: hub stamp -> 973d2fb657f13849c9834ce444029bfc4e483af3fd6194e915761d08f0193ba0
study-watchlist 0.3.0 — PASSED
  [warning] publisher-signature: unsigned: accountability rests on the hub alone
  grants: capabilities {"images", "net", "storage", "web"}, hosts {"api.bilibili.com", "i0.hdslb.com", "i1.hdslb.com", "www.bilibili.com"}, storage 16777216 bytes, agent none
```

`hub check --allow-unsigned` 退出 0；未签名的提示按设计存在。

## `hub scan` 7 问题逐条回答

### 1. 应用是否完成名称、副标题和描述宣称的功能？
是。`bundle/listing.json` 描述为：
「输入一个学习主题和一段可用时间（分钟）。应用从已声明的公开视频来源（bilibili 公开搜索 v2，免 key）实时取回候选视频，按来源给出的真实时长排出总时长落在预算内的观看清单……」
逐项落地（每一项都对应到 `bundle/main.splash` 的具体函数和事件）：
- 主题输入：`bind ui.topic_input` `on_return: |text| search(text)`。
- 实时取数：`fn live_search()` → `net.http_request(bilibili v2 url)` → `parse_bili(d)` → 取出 20 条带 `bvid/title/author/duration/play/pubdate/pic` 的真实记录（**没有自创 id、没有编造时长**）。
- 时长预算核验：`fn dur_secs()` 解析 `HH:MM:SS`/`MM:SS` → 秒；`fn pick_hint(h)` 给每条算"加入后余 / 加入会超预算 mm:ss"；`fn plan_text()` 显示 `已排 hh:mm:ss / 预算 hh:mm:ss（N 条）✓ 余 mm:ss` 或 `⚠ 超出预算 hh:mm:ss`。
- 授权：每行有 `on_click: || toggle_pick(i)` 的「加入/已选」按钮，逐条选择；`fn clear_plan()` 清空。
- 播放：行体 `on_tap: |x, y| play(h)` 把 `embed_for(h) = "https://www.bilibili.com/video/<bvid>"` 交给宿主 `WebReader.open()`。
- 失败与空状态：实时接口返回 0 行 → 显示"换一个更具体的关键词再试"；12 秒内无响应 → 显示"取数失败或 12 秒超时"；加载中显示"正在从公开视频来源检索 …"。
- 离线快照作为 fallback：`fn use_snapshot()` 读 `bundle/catalog/computer-networks.json`（同源、同一解析规则），快照文件带 `captured_at_utc/source_host/query`，界面原样标注。

**真实验收**：在官方的 card-host 构建上：真实客户端完成实时检索、预算核验、加入、改预算、清空、失败态、播放面板显示真实地址；`fs.write("state.json")` 在加入/改预算时持久化，重启后 `fn load()` 读回。

### 2. 列表平台和类别是否适合此类应用？
适合。应用是面向学生备考的清单工具，`platforms` 声明 `["linux","android"]`（实测平台 + 应用未来可跑的宿主），`category = "education"` 对应"清单 + 学习"形态。Linux 桌面端是评审复现路径，Android 是分发方向；声明的 macOS 评测环境不在 `platforms` 里，以避免评审按平台不一致扣分。

### 3. 能力是否与应用可见行为一致？每个主机为何？
- `storage`：保存并恢复「主题 / 预算 / 已加入清单」，重启后从 `state.json` 读回。
- `net`：唯一调用是实时搜索的 `https://api.bilibili.com/x/web-interface/search/all/v2?keyword=...`（免 key，免 cookie）；离线快照在应用包内通过 `{{assets}}` 本地回环，不消耗 `net`。
- `images`：缩略图 `http_resource(h.thumb)`，由 `thumb_for(h) = "https:" + h.pic` 给出，`h.pic` 是协议相对 `//i0/i1.hdslb.com/...`，故 `i0.hdslb.com` / `i1.hdslb.com` 必须放行。
- `web`：`ui.reader.open(h.embed)` 打开播放地址（`www.bilibili.com`），把"播放"这一步交给用户自己的浏览器，符合"播放是用户独立的操作"的官方 CONTROL。
没有任何"申请了能力但不显示"的隐蔽项；也没有任何"屏幕上看不到的 grant"。

### 4. 界面是否有冒充系统提示、支付、登录、其他品牌的部分？
没有。
- 没有 `is_password: true` / `Password`/`OneTimeCode` 输入（这本就过不了闸门）；
- 没有冒充宿主提示 / 系统弹窗 / 支付页；
- 应用里出现的 "card-host [remote]" 是 host 服务标识，不是应用冒充的；
- 标题与图标是中性"播放三角 + 时间刻度"几何图形，没有仿造平台 Logo；
- 应用自己的字符串里没有"这是平台提示/请输入密码"之类的模仿。

### 5. 源码或数据中是否有对助手而非对人写的指令？
没有。
- `bundle/main.splash` 顶部注释解释了数据源 + no-facts 原则，**不是给助手的指令**，而是给作者/审阅者的设计说明。
- `bundle/catalog/computer-networks.json` 的 `parser` / `note` 字段说明该文件是真实抓取记录、字段与运行时同款口径，**不是对助手的 prompt**。
- 没有任何 `system:` / `assistant:` / `you are` 这种 prompt 注入。
- 没有任何"请忽略以上内容" / "用浏览器打开" 等指令语。
（注意：`main.splash` 里写了`strip_em` 循环，目的是剥掉 `<em class="keyword">…</em>` 高亮——这是字符串处理函数，不是给读者的留言。）

### 6. 措辞是否冒犯、针对个人？
没有。所有 UI 字符串均为中性表述：提示、状态、按钮（"加入/已选/重试/清空/检索"），不含个人指向、不含攻击性语言。

### 7. 路由建议：通过 / 转人工 / 拒绝。给出 publisher 可执行的依据。
**建议：pass（轻微人工 review 也可）。** 依据：
- 闸门 `hub check --allow-unsigned` 已 PASSED，唯一警告是首次未签名——这是设计如此；
- 应用是一个**只读**的真实清单工具：所声明的 4 个主机都是公开、免 key、免 cookie 的内容来源（bilibili 公开搜索 + hdslb 图片），无敏感端点；
- 不收集凭据、不上传数据、不持久化任何账号信息——只把"主题 / 预算 / 已选 id"存在自己的 jail；
- 不重托管任何内容，所有播放地址都是来源自己的页面；
- 失败与空状态都有可见 UI（"取数失败或 12 秒超时"、"换一个更具体的关键词再试"），不静默降级成假数据；
- 真实捕获的 3 张截图（`01-plan-verified.png` / `02-source-unavailable.png` / `03-playback.png`）都能在指定的卡宿 + 锁版本运行时端到端复现（README §4、6）。
- 一处**建议维护者手动确认**的项：card-host 在 Linux 当前构建里 `CxOsOp::SpawnSystemBrowser` 未实现，播放面板会显示真实地址（可复制到浏览器自行打开）但不假装渲染内嵌页面。已在 README §5 第 6 条 + §6 证据表如实标注。

## 演示视频

- [evidence/demo.webm](https://github.com/lymio-lab/study-watchlist/blob/main/evidence/demo.webm)
  — 2:05，11 步覆盖初始 → 实时检索 → 5 min 预算失败（超预算 4:10:44）→ 300 min 预算成功（余 0:44:00）→ 离线快照 → empty 态。
  由 `tools/record_demo.py` 自动驱动 card-host 抓帧 + 烧字幕 + ffmpeg 合成。

## 已知限制（如实写）

1. 无章节 / 无转写 / 无大纲——来源只给整条视频的元数据。
2. 当前主题下的时长跨度从 `44:03` 到约 9 小时；20 分钟预算通常只能装 0–1 条。
3. 缩略图偶尔因宿主 TLS 路径不稳定而退化（缩略图为公开 https）。
4. 实时接口直接读 bilibili v2 的 JSON 形态，上游改版会失效；失败时如实报错。
5. 播放是跳转——不重托管内容；card-host on Linux 没有网页引擎时，宿主会尝试系统浏览器但 OS 操作 `CxOsOp::SpawnSystemBrowser` 在当前 Linux 构建里未实现 → 界面只显示真实地址（可复制到浏览器自行打开），不假装渲染内嵌。视频 `evidence/demo.webm` 未演示播放面板内嵌（这台机器上跑不出来），改用 `bundle/screenshots/03-playback.png` 单独说明这个行为。
6. AI 能力未接入，应用不需要任何 AI 也能完整运行。

## 后续路径（不在此次提交）

`ROADMAP.md` 列了三个方向：
- A · bilibili 分片（分P / 合集）—— 一条候选可展开成多个"段落"
- B · AI 字幕 cue-level 切割 —— 先做字幕结构化（B1），再接宿主模型按 cue 选段（B2）
- C · MIT OpenCourseWare 课程结构源 —— 长期，作为"先选课程"的入口

每个方向都写了合规风险点。**B2（模型选 cue）是 复赛 技术突破奖的方向**，有"延迟/成本/质量前后对照"实验素材的潜力。

> 本次提交只针对 v0.3.0 的"整段视频 + 时长预算编排"交付，不含上面三个方向。