# 录屏脚本（初赛 2–3 分钟演示）

> 工具：`card-host` 远程桥（`MAKEPAD_REMOTE`）+ 任意屏幕录像工具（ffmpeg、OBS、SimpleScreenRecorder 等）。
> 冻结版本：本地 `study-watchlist` 仓库 `v0.2.0`（commit `d6f9cd5`）的 bundle。

## 启动

```sh
cd /path/to/octosense-ws
OCTO=$(pwd)/OctoScript-App-Design-Flow/tools/octo

# 1) 把绑定源拷好（仅 cd 一次；以后 cargo build 即用）
cd OctoScript-App-Design-Flow && python3 tools/setup-native.py --check
cd ..

# 2) 构建 + 启动
cargo build --release -p octosense-card-host --manifest-path OctoSense-App-Hub/Cargo.toml
$OCTO run /path/to/study-watchlist/bundle --port 8200 --hidden --detach
sleep 3
echo "READY"
```

`--hidden` 隐藏窗口但仍渲染；屏幕录像工具照常录到画里。

## 节奏（建议 2.5 分钟）

**§1 开场（≤15 s）** —— 不操作，只录启动后的首屏。
- 标题"学习观看清单"。
- 副标题与说明。
- 两个标签：实时来源 / 离线快照。
- 输入：主题"计算机网络 期末复习"、预算 20 分钟。
- 状态行：输入一个学习主题，再点「检索」……

**§2 实时检索成功（≤30 s）** —— 让评审看到"实时从公开来源取回真实数据"。
- 点「检索」按钮（蓝色，在右侧）。
- 3 秒内，列表出 20 条，缩略图/标题/频道/时长/播放量/年龄/预算判定。
- 状态行：`实时来源返回 20 条结果 · 取数时间 2026-10-06 … UTC`。
- 列表上方：`以下 20 条来自实时来源 · 取数时间 … UTC`。

**§3 改预算 + 算术（≤30 s）** —— 展示"可核对的结果"。
- 点分钟预算输入框 → 改成 `60` 回车。
- 第一条（4h15m 课程）会立刻显示"加入会超预算 3:15:44"。
- 命词：用第一行 channel / duration 字段，复述"这条时长 4 小时 15 分钟，预算 60 分钟，超 3 小时 15 分钟"，强调**数字全部来自来源，不是我算的**。

**§4 加入 → 计划数学（≤20 s）** —— 核心可核对证据。
- 点第一条的「加入」（行右侧按钮，**不是行体**，行体打开播放）。
- 计划面板行立即更新：`已排 4:15:44 / 预算 1:00:00（1 条）⚠ 超出预算 3:15:44`。
- 这一行演示：时长加法 + 预算比较 + 超支/未超预算文案，全部由真实时长驱动。

**§6 离线快照 fallback（≤30 s）** —— "如果实时挂了也能跑"。
- 点「离线快照（真实记录）」标签。
- 状态行变成：`离线快照 · 取数时间 2026-10-06 … UTC · 来源 api.bilibili.com · query「计算机网络 期末复习」· 20 条`。
- 列表上方：`以下 20 条来自离线快照（真实抓取记录，字段与实时路径同一口径）`。
- 强调"快照不是练习数据，是同一来源同一解析规则的实时抓取快照"。
- 关掉计划（点「清空」），再点「实时来源」切回。

**§7 失败处理（≤30 s）** —— 必交的失败态演示。最短的演示（让评审看到"应用不会假装成功"）。
- 故意点一条行的「加入」留下计划（不强制）。
- 进入第 8 节播放：点任意一条**行体**（非按钮），打开播放面板。
- 播放面板显示：标题/频道/时长 + 真实 bilibili 播放地址。
- 评审可看到 card-host 在 Linux 上没有网页引擎，宿主 OS 操作 `SpawnSystemBrowser` 未实现 → 播放面板只显示可复制的地址，**不假装渲染**。
- 点「‹ 返回」回到清单。
- 重启 card-host（`curl 127.0.0.1:8200/quit` → 重启）→ 主题、预算、已加入清单都恢复（持久化证据）。

**§8 结尾（≤10 s）** —— 静止录 5 秒，显示"已知限制与待办"前的清单页。

## 录屏后期

1. 把 webm 传到仓库 `AppMap/` 或同目录 `/path/to/study-watchlist/release/`。
2. 用 `git tag` 打一个新的 git tag（如 `demo-2026-10-06`）指向录屏对应的 commit；或者把视频以 GitHub Release 形式挂出来。
3. 在 `Issue #13` 提交评论里附：
   - 队伍名：lymio-lab
   - GitHub 仓库地址：https://github.com/lymio-lab/study-watchlist
   - MiniMax 团队 ID：<已在前一步写入>
   - **演示视频地址**：<webm / release URL>
   - 冻结版本：v0.2.0（commit d6f9cd5）
4. 在 `OctoSense-org/OctoSense-App-Hub` 开 issue `Submit study-watchlist 0.2.0`，正文用 `APP_HUB_SUBMISSION.md`。

## 如果 Linux 上 card-host 播放面板的内嵌渲染没出来

如官方评测在 macOS 或更完整的 Linux 上跑：内嵌渲染会出现，截屏中能录到视频画面。本次脚本默认 card-host on Linux 没有网页引擎，应用**如实显示地址**，已在 bundle/03-playback.png 与 README §6 中明确标注。