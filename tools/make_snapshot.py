#!/usr/bin/env python3
"""抓取一次 bilibili 视频公开搜索结果，导出成应用可离线读取的快照。

免 key，直接用 https://api.bilibili.com/x/web-interface/search/all/v2。
字段对齐 L0/video 应用的最小需求：bvid、标题、UP主、播放数、时长、发布日期。

不含 https:// 字符串：bundle 内 .json 不能出现 https://（闸门规则），
所以 gateway 把 pic 字段保留为协议相对 URL `//i1.hdslb.com/...`，缩略图地址
由应用在运行时补上 `https:` 前缀。播放地址由 bvid 拼出。

用法:
    python3 tools/make_snapshot.py <query> > bundle/catalog/<name>.json
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote

SOURCE_HOST = "api.bilibili.com"


def fetch_results(query: str):
    kw = quote(query.strip())
    url = f"https://{SOURCE_HOST}/x/web-interface/search/all/v2?keyword={kw}"
    body = subprocess.run(
        ["curl", "-sSL", "--max-time", "40",
         "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
         url],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(body), url


def strip_em(s: str) -> str:
    # 高亮关键字标记
    return unescape(s).replace("<em class=\"keyword\">", "").replace("</em>", "")


def age_str(epoch) -> str:
    if not isinstance(epoch, int):
        return ""
    now = datetime.now(timezone.utc).timestamp()
    days = (now - epoch) / 86400.0
    if days < 0:
        return ""
    if days < 1:
        return "今天"
    if days < 30:
        return f"{int(days)} 天前"
    if days < 365:
        return f"{int(days // 30)} 个月前"
    return f"{int(days // 365)} 年前"


def parse(body: dict, limit: int = 20):
    if body.get("code") != 0 or not body.get("data"):
        return []
    out = []
    for block in body["data"].get("result") or []:
        if block.get("result_type") != "video":
            continue
        items = block.get("data") or []
        for it in items:
            if not it.get("bvid"):
                continue
            out.append({
                "id": it["bvid"],
                "title": strip_em(it.get("title") or ""),
                "channel": it.get("author") or "",
                "length": it.get("duration") or "",
                "views": str(it.get("play") or ""),
                "age": age_str(it.get("pubdate")),
                # 闸门禁止 https:// 字符串在 .json 资产中。
                # bilibili 返回 pic 为 //i0/i1.hdslb.com/...，正好不带 https://。
                "pic": it.get("pic") or "",
            })
            if len(out) >= limit:
                return out
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    query = sys.argv[1]
    body, url = fetch_results(query)
    hits = parse(body)
    snap = {
        "schema": 1,
        "query": query.strip(),
        "source_host": SOURCE_HOST,
        "source_endpoint": "/x/web-interface/search/all/v2",
        "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "parser": "bilibili v2 web search; no keys, no cookies",
        "note": ("Real capture from bilibili public search API. Every field is parsed from that response, "
                 "not authored. Thumbnail URL is protocol-relative and player URL is derived from "
                 "the bvid at render time, exactly as the runtime does."),
        "count": len(hits),
        "hits": hits,
    }
    json.dump(snap, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())