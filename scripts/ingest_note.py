#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一条口述，整理成一条结构化记录。

这是最小实现：只用规则（正则 + 关键词），不联网、不调用模型。目的是把
"数据长什么样"这件事固定下来，而不是替你做一个语音助手。

两个接入位置，代码里都标了 TODO：
    1 语音转文字：手机录音 -> 转写。用系统听写、或用你自己的转写服务。
    2 归整：把一段自由文本变成字段。规则版能覆盖常见说法，说法一多就不够。
      接模型的做法：把 prompts/02-归整记录.md 作为系统提示，把这段文本作为用户输入，
      要求它只输出 JSON，字段与 docs/数据与边界.md 一致，解析失败就丢掉不要猜。

用法：
    python3 scripts/ingest_note.py "6月12日 点位P-02 聊了4个 加了2个微信 意向中 周六再约"
    python3 scripts/ingest_note.py "..." --append notes.jsonl
"""

import argparse
import json
import re
import sys
from datetime import date

CN = {"零": 0, "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
NUM = r"[0-9]+|[零一两二三四五六七八九十]+"


def cn2int(s):
    """把「4」「四」「十二」「二十三」都变成 int。失败返回 None。"""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        left, _, right = s.partition("十")
        tens = CN.get(left, 1) if left else 1
        ones = CN.get(right, 0) if right else 0
        return tens * 10 + ones
    if len(s) == 1:
        return CN.get(s)
    return None


def grab(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else None


def parse_note(text, year=None):
    year = year or date.today().year

    month = grab(r"(\d{1,2})\s*月", text)
    day = grab(r"月\s*(\d{1,2})\s*[日号]", text)
    d = f"{year:04d}-{int(month):02d}-{int(day):02d}" if month and day else ""

    point = grab(r"(P-\d+)", text) or grab(r"点位\s*([A-Za-z0-9\-]+)", text) or ""

    reached = cn2int(grab(r"(?:聊了|接触|问了|搭话|谈了)\s*(" + NUM + r")\s*(?:个|位|人)", text))
    leads = cn2int(grab(r"(?:加了|留了|留资|要了|存了)\s*(" + NUM + r")\s*(?:个|位)?\s*(?:微信|电话|联系方式)", text))
    deals = cn2int(grab(r"(?:成交|成了|定了|签了)\s*(" + NUM + r")\s*(?:个|单)?", text))
    intent = grab(r"意向\s*(高|中|低)", text)

    next_step = grab(r"(?:下一步|再约|下次)[，,：: ]*\s*(.+)$", text) or ""
    if not next_step:
        m = re.search(r"(周[一二三四五六日末]|[今明后]天)[^，。,.]*$", text)
        next_step = m.group(0) if m else ""

    return {
        "date": d,
        "point_id": point,
        "owner": grab(r"(组员\s*[A-Za-z0-9]+)", text) or "",
        "reached": reached or 0,
        "leads": leads or 0,
        "deals": deals or 0,
        "intent": intent or "",
        "next_step": next_step.strip(),
        "raw": text,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", help="一条口述的原文")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--append", help="追加写入 jsonl 文件，默认只打印")
    args = ap.parse_args()

    rec = parse_note(args.text, args.year)

    # 缺关键字段就提示，不猜。填错一条记录，比少一条记录贵得多。
    gaps = [k for k in ("date", "point_id") if not rec[k]]
    if gaps:
        print(f"缺关键字段：{'、'.join(gaps)}。补一句再说一遍，不要让它猜。", file=sys.stderr)

    line = json.dumps(rec, ensure_ascii=False)
    if args.append:
        with open(args.append, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(f"已追加到 {args.append}")
    print(json.dumps(rec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
