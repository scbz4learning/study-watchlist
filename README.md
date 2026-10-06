# 学习观看清单 (study-watchlist)

> AgenticApp 黑客松 2026 · 初赛作品 · 赛道：**OctoSense 视频**
> 队伍：`lymio-lab`（scbz / lyz59）

一个 OctoSense 脚本应用（Octoscript app）。给它一个**学习主题**和一段**可用时间**，
它从已接入的公开视频来源（bilibili 公开搜索 v2，免 key）实时取回候选视频，按来源给出的
**真实时长**排出总时长**落在预算内**的观看清单，并逐条给出"加入后预算余量 / 超支量"。

**它不做什么（重要）**：不自己找数据源、不记录或编造视频 id、不描述视频内容、
不把时长当成可以估算的数字。所有事实性字段都来自运行时**声明的主机**上**该主机提供的
公开搜索 API**，取不到就如实显示失败，不用编造值填空。

---

## 1. 它解决什么任务

| | |
|---|---|
| **用户与场景** | 备考的学生：距离考试只剩一段零碎时间，需要在有限时间里挑出"该看什么" |
| **一句话意图** | 我有这个主题和这么多分钟，帮我排一份看得完的清单 |
| **需要的输入** | 学习主题（文字）、可用时间预算（分钟） |
| **一个必要操作** | 点条目右侧「加入」把视频计入计划 |
| **操作后的可观察结果** | 计划行实时显示 `已排 hh:mm:ss / 预算 hh:mm:ss（N 条）`，并给出 `余 hh:mm:ss` 或 `⚠ 超出预算 hh:mm:ss`；每条候选行同时显示"加入后余/超支多少" |
| **Agent 负责** | 理解主题与预算 → 从公开来源实时取回候选 → 按真实时长排出落在预算内的清单 → 逐条给出预算判定 → 把地址交给用户去播放 |
| **用户负责** | 定主题和预算、决定加入哪些、最终点开哪一条 |
| **失败/空状态** | 取数失败、12 秒超时、来源无结果，三种都如实显示，并给出「重试」与「离线快照」 |
| **本次不包含** | 章节/分段锚点、转写、自动帮用户"学会"、代替用户播放或订阅 |

### 为什么"找来源"不在应用职责内

官方对 OctoSense 应用的硬性规则（App-Design-Flow `AGENTS.md`、`SCRIPT-API.md`、
App Hub `PUBLISHING.md`）：

- 「**No secrets in apps.** … no API key or token in the bundle.」
- 「ALL displayed data must come from the existing `sys.*` helpers — **no new data sources, no model-authored values**.」
- 「**Ids are facts.** The card declares a QUERY and the runtime finds the videos.」
- no-Facts：事实由数据能力提供，**不得编造状态、操作成功或执行结果**。

**Script app 的具体表现**（比 L0 卡多一项：可以调用 `net.http_request`）：
「A script app fetches what it declares (ADR 0004): an `https://` address may name only a
host in the manifest's `network.hosts`」（App Hub `gate.rs`）。

所以本应用只**声明意图 + 使用白名单主机的公开 API**；数据源、凭据、可用性都由平台/来源负责。
当前声明的是 bilibili 公开搜索 API（免 key），不是 YouTube——后者在比赛时区（CST）的可达性
不适合做实时路径（同样的数据-能力模式可以日后切换到任意免 key 主机）。

---

## 2. 数据来源（两种，界面上分别标注，不混为一谈）

| 模式 | 数据来源 | 界面标注 |
|---|---|---|
| **实时来源**（默认） | bilibili 公开搜索 v2：`https://api.bilibili.com/x/web-interface/search/all/v2?keyword=…`，免 key，免 cookie；取前 20 条 | `实时来源返回 N 条结果 · 取数时间 … UTC` |
| **离线快照** | 应用包内 `bundle/catalog/computer-networks.json` | `离线快照 · 取数时间 … · 来源 api.bilibili.com · query「…」· N 条`，列表上方再标一次 |

实时接口返回的字段：`bvid / title / author / duration / play / pubdate / pic`。
- **没有章节、没有转写、没有大纲**——所以本应用的最小观看单元是"整条视频"，不假装有更细的锚点。
- **缩略图**是协议相对 URL（`//i0/i1.hdslb.com/...`），运行时补 `https:` 前缀。
- **播放地址**用 `bvid` 拼出：`https://www.bilibili.com/video/<bvid>`。
- 标题中 `<em class="keyword">…</em>` 高亮标记会被剥掉（关键字是检索词，不是事实）。

**离线快照不是练习数据，也不是模型编的**：它是用 `tools/make_snapshot.py` 从
公开来源**真实抓取**后写下的记录，解析规则与实时路径完全一致。
文件里带 `captured_at_utc`、`source_host`、原始 query，界面上原样显示。

重新生成快照（需要能访问该来源的网络）：

```sh
python3 tools/make_snapshot.py "计算机网络 期末复习" > bundle/catalog/computer-networks.json
```

---

## 3. 权限与隐私

| 能力 | 为什么需要 |
|---|---|
| `storage` | 记住主题、预算和已加入的清单，重启后恢复 |
| `net` | 向已声明的来源主机发起 GET，取回候选与缩略图 |
| `images` | 加载候选视频的缩略图（公开 https） |
| `web` | `WebReader.open(embed)` 把播放地址交给宿主 |

声明主机：`api.bilibili.com`（搜索）、`www.bilibili.com`（播放页）、`i0.hdslb.com` / `i1.hdslb.com`（缩略图）。

- **不收集任何密码、口令、验证码、API key 或 token**（官方硬性要求，闸门会拒）。
- 不登录、不写任何账号状态、不上传任何数据；只有 GET，没有 POST。
- 本地只存"主题 / 预算 / 已加入清单"三项，存在应用自己的 jail 里，卸载即清除。
- 不重托管任何内容，只做**引用与跳转**：播放跳转到来源自己的页面。
- 拒绝/失败行为：拒绝联网或取不到数据 → 明确显示失败并给恢复路径，不静默降级成假数据。

---

## 4. 运行与复现

需要先有一个**锁版本**的 OctoSense 工作区（见
[OctoScript-App-Design-Flow](https://github.com/OctoSense-org/OctoScript-App-Design-Flow)
的 `docs/QUICKSTART.md`）。本次证据所用版本：

| 组件 | 版本 / 提交 |
|---|---|
| `OctoScript-App-Design-Flow` | `main`（`tools/octo`） |
| `OctoSense-App-Hub` | `main`（`card-host` / `hub`，本地 release 构建） |
| `makepad` | `c155f61d0e1600d2ec474209374444a38a09a470` |
| `octoscript` | `5991dfae9344589e732b2605b530f788e8bbcd11` |
| `octoscript-makepad` | `2cc5ef37d7d6a3d2992673389ce74488f7bb2d87` |
| 运行平台 | **Linux（Ubuntu 24.04, X11），本机自测；官方仅验证 macOS** |

```sh
OCTO=<path-to>/OctoScript-App-Design-Flow/tools/octo

# 1) 运行（无头，端口任意）
$OCTO run bundle --port 8141 --hidden --detach

# 2) 驱动 + 截图
curl -s 127.0.0.1:8141/click?x=<x>&y=<y>&wait=1
$OCTO shot 8141 out.png

# 3) 收尾
curl -s 127.0.0.1:8141/quit

# 4) 准入闸门
$OCTO check bundle        # 期望 ... PASSED（只留 unsigned warning）
```

Linux 上首次构建 `card-host` 需要系统图形库（wayland / X11 / ALSA / GL / Vulkan），
依赖清单见 octosense 工作区 `makepad/tools/linux_deps.sh`。

**复现"预算核验"这条证据只要 5 步**：

1. 启动后保持默认主题「计算机网络 期末复习」，点「检索」 → 实时来源 3 秒内返回约 20 条
2. 点分钟预算输入框，改成 `60` 回车
3. 第一行（时长 `255:44`，约 4 小时）会显示"加入会超预算 3:55:44"
4. 点该行的「加入」（在「加入」按钮上，不是行体） → 计划行显示
   `已排 4:15:44 / 预算 1:00:00（1 条） ⚠ 超出预算 3:15:44`
5. 任何时候切到「离线快照（真实记录）」 → 同名同预算下用一份标注了取数时间的真实记录复演

---

## 5. 已知限制（如实写，不含糊）

1. **无章节 / 无转写 / 无大纲**：来源只给整条视频的元数据。所以"1 分钟速览某一节课的某一段"
   做不到；最小观看单元是整条视频。
3. **时长跨度大**：当前主题下的预备时长分布在 `44:03` ~ `9 小时`：20 分钟预算通常只能装 0–1 条；
   60 分钟预算通常装 0–1 条；**应用不假装覆盖整个主题**，只显示"这次预算排入了什么、没覆盖什么"。
4. **缩略图偶尔不显示**：从同一宿主环境对图片主机的 TLS 路径有时返回 `SSL_read failed`，
   失败时退化为只显示前两行的标题/数据元 + 右侧按钮，但不影响功能。
5. **依赖上游页面结构**：实时接口直接读来源公开搜索 API 的 JSON 形态，上游改版会失效。
   失败时应用如实报错，不假装成功。
6. **播放是跳转**：点条目会用宿主 `WebReader` 打开视频原页面（外链），本应用**不**重托管内容。
   card-host 在 Linux 上没有网页引擎，宿主会尝试系统浏览器（`CxOsOp::SpawnSystemBrowser`），
   该 OS 操作在当前构建里未实现 → 界面只显示真实地址（可复制到浏览器自行打开），不假装播放成功。
7. **AI 能力未接入**：应用没有任何推理环节，`model` / `octos.*` 在 `card-host` 中不提供服务，
   所以本应用**不依赖**任何 AI 功能也能完整运行。

---

## 6. 证据与状态

| 项 | 状态 |
|---|---|
| `tools/octo check bundle` | ✅ **PASSED**（只有 unsigned 警告）：
  `study-watchlist 0.3.0 — PASSED` / `[warning] publisher-signature: unsigned: accountability rests on the hub alone` /
  `grants: capabilities {"images","net","storage","web"}, hosts {"api.bilibili.com","i0.hdslb.com","i1.hdslb.com","www.bilibili.com"}, storage 16777216 bytes, agent none` |
| `bundle/screenshots/01-plan-verified.png` | ✅ 真实捕获：bilibili 实时返回 20 条 + 预算 20 分钟 + 一条已加入 + `已排 4:15:44 / 预算 20:00（1 条） ⚠ 超出预算 3:55:44`；算术可用每条视频的 length 字段逐条复核 |
| `bundle/screenshots/02-source-unavailable.png` | ✅ 真实捕获：实时来源空状态——宿主主机临时不可达时显示「换一个更具体的关键词再试」；同样代码路径在 12 秒取数失败时也会显示「取数失败或 12 秒超时」 |
| `bundle/screenshots/03-playback.png` | ✅ 真实捕获：点条目后进入播放面板，标题/频道/时长 + 真实 bilibili 播放地址 `https://www.bilibili.com/video/BV1H4kwYHEcR`，可复制到浏览器自行打开 |
| `evidence/demo.webm` | ✅ 2:05 演示视频：11 步覆盖初始 → 实时检索 → 5 min 预算失败（超 4:10:44）→ 300 min 预算成功（余 0:44:00）→ 离线快照 → empty 态；脚本 `tools/record_demo.py` 自动驱动 card-host 抓帧 + 烧字幕 + ffmpeg 合成 |
| 一次操作 + 可核对结果 | ✅ 加入一条 → 计划总时长与预算差额实时更新（算术可用每条视频的 length 字段逐条复核） |
| 一个失败或空状态 | ✅ 失败态（取数失败 / 12 秒超时）、空结果态、加载态三态齐全 |
| 实时路径 | ✅ 已在联网环境实测成功（bilibili v2 搜索, 20 条, <3 秒） |
| 播放 | ⚠️ 播放面板可正常进入并显示真实地址，但 card-host on Linux 没有网页引擎，宿主无法在窗口内渲染页面（OS 操作 `CxOsOp::SpawnSystemBrowser` 在此构建未实现）。在 macOS 桌面端应可走通；**已如实标注** |
| 持久化（重启恢复） | ✅ `state.json` 在加入/改预算时落盘，boot() 时读回 |

---

## 7. 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。

---

## 8. 后续路径（不进初赛交付）

初赛交付停在 v0.3.0 的"整段视频 + 时长预算编排"上。后续（复赛 / 技术突破）的演进在
[ROADMAP.md](ROADMAP.md) 里展开，三个方向：

- **A · bilibili 分片选择**：分P / 合集解析，让每条候选能展开成多个"段落"颗粒
- **B · AI 字幕 cue-level 切割**：先做字幕结构化（B1），再接宿主模型按 cue 选段（B2）
- **C · MIT OpenCourseWare 课程结构源**：长期，作为"先选课程再选视频"的入口

每个方向都标了"比赛合规"风险点——尤其 B2 必须守住 no-facts 边界，所有 AI 输出
必须标"AI 建议"而不是事实。