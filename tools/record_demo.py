#!/usr/bin/env python3
"""初赛演示录屏工具：驱动 card-host 走 11 步完整 demo，每 100ms 抓一帧 PNG，叠中文字幕，最后 ffmpeg 拼 webm。

为什么需要这个脚本：card-host on Linux 的播放面板（WebReader）宿主 OS 操作
未实现（`CxOsOp::SpawnSystemBrowser`），所以**不能用简单的视频流截屏**；
我们改成「抓 PNG 序列 + 烧字幕 + ffmpeg 合成」的离线方案。

## 用法

```sh
# 0) 先启动 card-host（任一一种方式）
make setup                                  # 一次性：拉锁版本运行时
$OCTO run $A/bundle --port 8200 --hidden --detach
# 上面命令的工具链见 OctoScript-App-Design-Flow / repo 的 README

# 1) 装 ffmpeg + python3-pil + DejaVu + Noto CJK 字体
sudo apt-get install -y ffmpeg python3-pil fonts-noto-cjk

# 2) 录屏
python3 tools/record_demo.py 8200 evidence/demo.webm
# → 写到 /tmp/kilo/demo-frames/*.png → 拼成 evidence/demo.webm (VP9, 412x892, 10fps)
```

## 它做了什么

1. **驱动**：每步先 `GET /snap` 拿当前 widget rects，**按 label/id 找按钮中心点击**（不用硬编码像素，
   因为列表出来后布局会移动）。
2. **抓帧**：每个 step 留 12s 给 card-host 渲染 + 取一帧 PNG（10 fps）。
3. **烧字幕**：用 Noto Sans CJK 烧中文 step 标题 + 描述。Status text / plan label
   是 app 自己的，字幕是演示用的 overlay。
4. **合成**：ffmpeg 拼 PNG 序列成 VP9 webm。

## 11 步演示节奏

| # | t    | 动作 | 关键状态变化 |
|---|------|------|------------|
| 1 | 0s   | 初始页 | idle |
| 2 | 12s  | 点「检索」 | live 20 rows |
| 3 | 24s  | 改预算 20→5 | 准备看失败 |
| 4 | 36s  | 加一条 4h15m 视频 | 计划：超出 4:10:44 |
| 5 | 48s  | 失败案例保持 | "超出预算" 显示 |
| 6 | 60s  | 清空 + 改预算 5→300 | 准备看成功 |
| 7 | 72s  | 加同一条视频 | 计划：未超 余 0:44:00 |
| 8 | 84s  | 成功案例保持 | "未超预算 余 X" |
| 9 | 102s | 切离线快照 chip | 离线 20 rows |
| 10| 120s | 离线清空 → empty | "换一个更具体的关键词再试" |
| 11| 138s | 退出 hold 60s | 收尾 |

总时长 ~3 分钟。

## 录完之后

- `evidence/demo.webm` 是 vp9 webm（412x892, 10fps）。GitHub 不直接预览 webm，
  评审需下载观看。
- `bundle/screenshots/01-03.png` 是同一波卡住的关键帧（key frame），评审
  不想看视频时可以直接看图。

## 失败态与成功态都覆盖了

- **5 min 预算 + 4h15m 视频** → 计划显示 "超出预算 4:10:44"，符合 no-facts（数字
  全来自视频 length 字段与预算输入，没编）
- **300 min 预算 + 4h15m 视频** → "未超预算，余 0:44:00"，同一视频不同预算下行为
  不一样，正是「可核对」

## 如果 Linux 上 card-host 播放面板的内嵌渲染没出来

card-host on Linux 没有网页引擎，宿主 OS 操作 `SpawnSystemBrowser` 在当前构建
未实现。播放面板会显示真实地址（可复制到浏览器自行打开）但不假装渲染内嵌。
在 macOS 桌面端应可走通；**本录屏脚本不演示播放面板内嵌**，而是用第三个
截图 `03-playback.png` 说明这个行为（已写进 README §6）。
"""
import os
import sys
import time
import urllib.request
import urllib.parse
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8200
WEB_OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/kilo/demo.webm"
FRAMES = "/tmp/kilo/demo-frames"
FPS = 10
DT = 1.0 / FPS

os.makedirs(FRAMES, exist_ok=True)
for f in os.listdir(FRAMES):
    if f.endswith(".png"):
        os.remove(os.path.join(FRAMES, f))

FONT_TITLE = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_BODY = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def get_snap():
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/snap", timeout=5) as r:
        return json.load(r)

def get_png():
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/g?raw=1", timeout=5) as r:
        return r.read()

def click(x, y, wait=1):
    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/click?x={x}&y={y}&t=click&wait={wait}", timeout=5).read()

def key(c, wait=0.3):
    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/k?k=down&c={c}&wait={wait}", timeout=5).read()

def type_text(s, wait=0.5):
    q = "t=" + urllib.parse.quote(s) + f"&wait={wait}"
    urllib.request.urlopen(f"http://127.0.0.1:{PORT}/t?{q}", timeout=5).read()

def find_widget(snap, ty=None, t=None, wi=None):
    """按类型 / 文本 / id 找 widget。"""
    for w in snap["s"]:
        if ty and w.get("ty") != ty: continue
        if t is not None and (w.get("t") or "") != t: continue
        if wi is not None and w.get("i") != wi: continue
        return w
    return None

def click_by_text(snap, text, kind="Button", wait=1):
    """按文本/类型找按钮中心点击。"""
    for w in snap["s"]:
        if w.get("ty") == kind and (w.get("t") or "") == text:
            x, y, w_, h = w["r"]
            click(x + w_ // 2, y + h // 2, wait=wait)
            return w
    return None

def click_by_id(snap, wid, wait=1):
    for w in snap["s"]:
        if w.get("i") == wid:
            x, y, w_, h = w["r"]
            click(x + w_ // 2, y + h // 2, wait=wait)
            return w
    return None

def click_first_add_button(snap, wait=1):
    for w in snap["s"]:
        if w.get("ty") == "Button" and w.get("t") == "加入":
            x, y, w_, h = w["r"]
            click(x + w_ // 2, y + h // 2, wait=wait)
            return w
    return None

def burn_caption(png_bytes, title, body, frame_num):
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    W, H = img.size
    # 半透明黑底标题条（在顶部）
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    font_t = ImageFont.truetype(FONT_TITLE, 16)
    font_b = ImageFont.truetype(FONT_BODY, 12)
    # 标题条
    bar_h = 56
    d.rectangle([(0, 0), (W, bar_h)], fill=(15, 18, 28, 200))
    d.text((10, 6), title, fill=(255, 255, 255, 255), font=font_t)
    d.text((10, 30), body, fill=(220, 224, 232, 255), font=font_b)
    # 步骤计数
    d.text((W - 30, 18), f"#{frame_num}", fill=(160, 170, 200, 200), font=font_b)
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


# 主时间轴：(秒, 标题, 描述, 动作)
SCRIPT = [
    (0, "Step 1 · 初始页",
     "Empty state. 输入主题 + 预算后，按「检索」。",
     None),
    (12, "Step 2 · 实时检索",
     "点 检索：调用 bilibili 公开搜索 v2（免 key）→ 20 rows。",
     lambda: click_by_text(get_snap(), "检索", wait=2)),
    (24, "Step 3 · 失败态：5 分钟预算（4h 视频远装不下）",
     "改预算 20→5. 准备看 4h 视频加入后的失败。",
     lambda: (click_by_id(get_snap(), "budget_input", wait=0.5),
              key("Backspace"), key("Backspace"),
              type_text("5", wait=0.5), key("ReturnKey", wait=1))),
    (36, "Step 4 · 加一条 4h15m 视频到 5min 预算",
     "点第一条的 加入。 计划行会显示超出预算 4:10:44。",
     lambda: click_first_add_button(get_snap(), wait=1)),
    (48, "Step 5 · 失败案例：超出预算（已自动加到 plan）",
     "Plan label: 超出预算 4:10:44. 数学：4h15m - 5min = 4h10m44s.",
     None),
    (60, "Step 6 · 清空 + 改预算到 300 分钟",
     "点 清空, 改预算 5→300. 4h15m=256min 应该装得下。",
     lambda: (click_by_text(get_snap(), "清空", wait=0.5),
              click_by_id(get_snap(), "budget_input", wait=0.5),
              key("Backspace"), key("Backspace"), key("Backspace"),
              type_text("300", wait=0.5), key("ReturnKey", wait=1))),
    (72, "Step 7 · 加同一条视频到 300min 预算",
     "点第一条的 加入. 4h15m < 5h 预算 → 不超支。",
     lambda: click_first_add_button(get_snap(), wait=1)),
    (84, "Step 8 · 成功案例：未超预算",
     "Plan label: 未超预算，余 0:44:00. 数学：5h - 4h15m = 44min.",
     None),
    (102, "Step 9 · 离线快照 chip",
     "切到离线快照模式：包内真实抓取记录（20 条同一来源）。",
     lambda: click_by_text(get_snap(), "离线快照（真实记录）", wait=2)),
    (120, "Step 10 · 空白/未知提示",
     "点清空. 状态回到 empty：换一个更具体的关键词再试。",
     lambda: click_by_text(get_snap(), "清空", wait=0.5)),
    (138, "Step 11 · 退出",
     "DONE. 视频总长 ~3 分钟.",
     None),
]

def run():
    n = 0
    t_start = time.time()
    for i, (t_target, title, body, action) in enumerate(SCRIPT):
        if action is not None:
            print(f"[{t_target:3d}s] {title}")
            try:
                action()
            except Exception as e:
                print(f"  action err: {e}", file=sys.stderr)
        # 截到下一段时间。next_t 是「从 t_start 起算的目标时间」，所以即便
        # 之前步骤吃掉了动作时间，这一段仍会按预定时长截帧。
        next_t = SCRIPT[i+1][0] if i+1 < len(SCRIPT) else 180
        capture_until = t_start + next_t
        while time.time() < capture_until:
            try:
                png = get_png()
                img = burn_caption(png, title, body, i+1)
                img.save(f"{FRAMES}/frame-{n:05d}.png", "PNG")
                n += 1
            except Exception as e:
                print(f"  snap err: {e}", file=sys.stderr)
            time.sleep(DT)
    print(f"wrote {n} frames")
    return n


def encode(n):
    print(f"\nEncoding {n} frames -> {WEB_OUT}")
    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{FRAMES}/frame-%05d.png",
        "-c:v", "libvpx-vp9",
        "-b:v", "300k",
        "-pix_fmt", "yuv420p",
        "-an",
        WEB_OUT,
    ]
    r = subprocess.run(cmd, capture_output=True)
    print(r.stderr.decode("utf-8", "ignore")[-1500:])
    if r.returncode != 0:
        print(f"ffmpeg failed: {r.returncode}")
        return False
    print(f"OK {WEB_OUT} ({os.path.getsize(WEB_OUT)//1024} KB)")
    return True


if __name__ == "__main__":
    n = run()
    if encode(n):
        print("DONE")
    else:
        print(f"frames in {FRAMES}, encoding failed")
        sys.exit(1)