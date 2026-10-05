# 学习观看清单 (study-watchlist)

> AgenticApp 黑客松 2026 · 初赛作品 · 赛道：**OctoSense 视频**
> 队伍：`lymio-lab`（scbz / lyz59）

一个 OctoSense 脚本应用（Octoscript app）。给它一个**学习主题**和一段**可用时间**，
它从已接入的公开视频来源取回候选视频，按来源给出的**真实时长**排出总时长
**落在预算内**的观看清单，并逐条给出"加入后预算余量 / 超支量"。

**它不做什么（重要）**：不自己找数据源、不记录或编造视频 id、不描述视频内容、
不把时长当成可以估算的数字。所有事实性字段都来自运行时提供的数据能力
（`sys.video`），取不到就如实显示失败，不用编造值填空。

---

## 1. 它解决什么任务

| | |
|---|---|
| **用户与场景** | 备考的学生：距离考试只剩一段零碎时间，需要在有限时间里挑出"该看什么" |
| **一句话意图** | 我有这个主题和这么多分钟，帮我排一份看得完的清单 |
| **需要的输入** | 学习主题（文字）、可用时间预算（分钟） |
| **一个必要操作** | 点条目右侧「加入」把视频计入计划 |
| **操作后的可观察结果** | 计划行实时显示 `已排 mm:ss / 预算 mm:ss（N 条）`，并给出 `余 mm:ss` 或 `⚠ 超出预算 mm:ss`；每条候选行同时显示"加入后余/超支多少" |
| **Agent 负责** | 理解主题与预算 → 从来源取回候选 → 按真实时长排出落在预算内的清单 → 逐条给出预算判定 → 执行打开 |
| **用户负责** | 定主题和预算、决定加入哪些、最终点开哪条 |
| **失败/空状态** | 取数失败、12 秒超时、来源无结果，三种都如实显示，并给出「重试」与「离线快照」 |
| **本次不包含** | 章节/分段锚点、转写、自动帮用户"学会"、代替用户播放或订阅 |

### 为什么"找来源"不在应用职责内

官方对 OctoSense 应用的硬性规则（App-Design-Flow `AGENTS.md`、`SCRIPT-API.md`、
App Hub `PUBLISHING.md`）：

- 「**No secrets in apps.** … no API key or token in the bundle.」
- 「ALL displayed data must come from the existing `sys.*` helpers — **no new data
  sources, no model-authored values**.」（`a2app/framework.md`）
- 「**Ids are facts.** The card declares a QUERY and the runtime finds the videos.」
  （`a2app-l0/framework.md`，并明确说让应用自己攒 video id 的旧做法 "was wrong for
  a whole release"）
- no-Facts：事实由数据能力提供，**不得编造状态、操作成功或执行结果**。

所以本应用只**声明意图**并消费平台能力 `sys.video`；数据源、凭据、可用性都由平台负责。

---

## 2. 数据来源（两种，界面上分别标注，不混为一谈）

| 模式 | 数据来源 | 界面标注 |
|---|---|---|
| **实时来源**（默认） | 运行时助手 `sys.video(query, index, field)`，读取公开视频来源的检索结果页（无 key） | `实时来源返回 N 条结果 · 取数时间 … UTC` |
| **离线快照** | 应用包内 `bundle/catalog/computer-networks.json` | `离线快照 · 取数时间 … · query「…」· N 条`，列表上方再标一次 |

`sys.video` 提供的字段：`id / title / channel / length / views / age / thumb / embed`。
**没有章节、没有转写、没有大纲**——所以本应用的最小观看单元是"整条视频"，不假装有更细的锚点。

**离线快照不是练习数据，也不是模型编的**：它是用
`tools/make_snapshot.py` 从公开来源**真实抓取**后写下的记录，解析规则与运行时
`sys.video` 完全一致（复刻 `makepad/widgets/src/splash.rs` 的 `yt_parse_results`），
文件里带 `captured_at_utc`、`source_url`、原始 `query`，界面上原样显示。

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
| `web` | `WebReader.open(embed)` 打开视频原页面播放 |

声明主机：`www.youtube.com`、`m.youtube.com`、`i.ytimg.com`。

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

**复现"预算核验"这条证据只要 4 步，且不需要网络**：

1. 启动后点「离线快照（真实记录）」 → 状态行显示快照的取数时间与 query，列表出 11 条
2. 点分钟预算输入框，改成 `120` 回车
3. 每条候选行显示"加入后余 / 加入会超预算 mm:ss"
4. 点任意一条「加入」 → 计划行显示 `已排 mm:ss / 预算 2:00:00（N 条）✓ 未超预算，余 mm:ss`

---

## 5. 已知限制（如实写，不含糊）

1. **无章节 / 无转写 / 无大纲**：`sys.video` 只给整条视频的元数据。所以"1 分钟速览某一节课的某一段"
   做不到；最小观看单元是整条视频。想要章节级锚点必须新增一个平台数据能力（改运行时 + 上游 PR）。
2. **视频不可分割**：真实时长在 10:38–1:40:06 之间（见快照），因此 20 分钟预算最多只能装 1–2 条。
   应用**不做**"20 分钟覆盖全部课程"这种承诺，只显示"这次预算排入了什么、没覆盖什么"。
3. **缩略图可能不显示**：本机自测环境下运行时的 TLS 客户端无法完成对外 HTTPS 请求
   （`SSL_read failed: unexpected eof while reading`），所以**实时取数与缩略图在本机自测中均不可用**；
   这正是本作品把失败态做扎实的原因，也是为什么用**离线真实快照**给出可核对的正常态证据。
   在能正常联网的环境中，实时路径与缩略图预期可用——但**尚未在联网环境复核**（见 §6）。
4. **实时来源依赖上游页面结构**：`sys.video` 读取公开视频来源的检索结果页，上游改版会失效。
   失败时应用如实报错，不假装成功。
5. **播放是跳转，不是内嵌**：点条目会用宿主 `WebReader` 打开视频原页面（该页面自带平台的
   "打开 App"提示），本应用不重托管内容。
6. **AI 能力未接入**：`sys.video` 之外没有任何推理环节；`model` / `octos.*` 在 `card-host`
   中不提供服务，所以本应用**不依赖**任何 AI 功能也能完整运行。若后续要用"宿主模型"解释
   入选理由，那是复赛的技术突破方向，不影响初赛可运行性。

---

## 6. 证据与状态

| 项 | 状态 |
|---|---|
| `bundle/screenshots/01-plan-verified.png` | ✅ 真实捕获：离线快照 11 条真实结果 + 预算 120 分钟 + 一条已加入 + `已排 44:42 / 预算 2:00:00 ✓ 余 1:15:18` |
| `bundle/screenshots/02-source-unavailable.png` | ✅ 真实捕获：实时路径 12 秒超时后的失败态 + 「重试」 |
| 一次操作 + 可核对结果 | ✅ 加入一条 → 计划总时长与预算差额实时更新（算术可用来源时长复核） |
| 一个失败或空状态 | ✅ 失败态（超时/取数失败）、空结果态、加载态三态齐全 |
| 实时（联网）路径 | ⚠️ **未在联网环境复核**：本机 TLS 被环境阻断。代码路径已按官方 `os.youtube` 的
  三态（`"—"` 加载 / `"n/a"` 失败 / `""` 末条）+ `loaded_q` 守卫实现，待复核环境补录证据 |
| 播放 | ⚠️ 同上，`WebReader.open(embed)` 已接好，待联网环境复核截图 |

---

## 7. 许可证

Apache License 2.0，见 [LICENSE](LICENSE)。
