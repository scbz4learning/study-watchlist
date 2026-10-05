#!/usr/bin/env python3
"""抓取一次公开视频来源的检索结果，导出成应用可离线读取的快照。

这个脚本**复刻**运行时 `sys.video` 的解析规则（`makepad/widgets/src/splash.rs`
的 `yt_parse_results`），所以快照里的字段和线上路径取到的字段是同一套口径，
不是另编一份数据。

**不含任何绝对 URL**：App Hub 闸门规定 bundle 内的 `.json` 等资产不得出现
`https://` 字符串（`hub` 的 `external_references`），所以这里只存视频 id 与
纯文本字段；缩略图与播放地址由 `bundle/main.splash` 用与运行时相同的规则从
id 拼出（`i.ytimg.com/vi/<id>/mqdefault.jpg` 与 `m.youtube.com/watch?v=<id>`）。
provenance 用主机名 + query + 取数时间表达，不用 URL。

用法:
    python3 tools/make_snapshot.py <query> > bundle/catalog/<name>.json
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone

SOURCE_HOST = "www.youtube.com"

# 与 makepad 的 yt_search_url 一致：逐字节百分号编码，空格转 '+'
def yt_search_url(query: str) -> str:
    q = []
    for b in query.strip().encode("utf-8"):
        c = chr(b)
        if c.isascii() and (c.isalnum() or c in "-_."):
            q.append(c)
        elif c == " ":
            q.append("+")
        else:
            q.append("%%%02X" % b)
    return "https://www.youtube.com/results?search_query=" + "".join(q)


def unescape(s: str) -> str:
    # yt_unescape 的等价物：\uXXXX、\n、\"、\\、\/
    def uni(m):
        return chr(int(m.group(1), 16))

    s = re.sub(r"\\u([0-9a-fA-F]{4})", uni, s)
    s = s.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\").replace("\\/", "/")
    return s


def pick(win: str, open_key: str) -> str:
    i = win.find(open_key)
    if i < 0:
        return ""
    rest = win[i + len(open_key):]
    j = rest.find('"')
    return unescape(rest[:j]) if j >= 0 else ""


def nested(win: str, obj: str, key: str) -> str:
    i = win.find(obj)
    if i < 0:
        return ""
    scope = win[i:i + 400]
    return pick(scope, key)


def parse(body: str, limit: int = 20):
    out, at = [], 0
    mark = '"videoRenderer":{"videoId":"'
    while True:
        found = body.find(mark, at)
        if found < 0:
            break
        start = at = found + len(mark)
        end = body.find('"', start)
        if end < 0:
            break
        vid = body[start:end]
        if len(vid) != 11 or any(h["id"] == vid for h in out):
            continue
        win = body[start:start + 2600]
        title = pick(win, '"title":{"runs":[{"text":"')
        if not title:
            continue
        length = nested(win, '"lengthText":{', '"simpleText":"') or "LIVE"
        # 只保留纯文本字段；缩略图/播放地址不落盘（闸门禁止资产内含 https URL，
        # 且它们能从 id 唯一推出，见模块 docstring）。
        out.append({
            "id": vid,
            "title": title,
            "channel": pick(win, '"longBylineText":{"runs":[{"text":"'),
            "length": length,
            "views": pick(win, '"viewCountText":{"simpleText":"'),
            "age": pick(win, '"publishedTimeText":{"simpleText":"'),
        })
        if len(out) >= limit:
            break
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    query = sys.argv[1]
    url = yt_search_url(query)
    body = subprocess.run(
        ["curl", "-sS", "--max-time", "40", "-A",
         "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
         url],
        check=True, capture_output=True, text=True,
    ).stdout
    hits = parse(body)
    snap = {
        "schema": 1,
        "query": query.strip(),
        "source_host": SOURCE_HOST,
        "source_kind": "public video search results page",
        "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "parser": "replicates makepad widgets/src/splash.rs yt_parse_results",
        "note": "Real capture from the public video source. Every field is parsed from that page, not authored. Thumbnail and player addresses are derived from the id at render time, exactly as the runtime does.",
        "count": len(hits),
        "hits": hits,
    }
    json.dump(snap, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
