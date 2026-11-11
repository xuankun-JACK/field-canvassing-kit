#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漏斗统计：把点位表与记录表合起来，按点位和按人各出一张表。

只做聚合，不做判断。判断（这个点位该不该放弃、这个人是不是方法有问题）留给人。

用法：
    python3 scripts/funnel.py --points samples/points.example.csv \
                              --notes samples/notes.example.json
    python3 scripts/funnel.py --points ... --notes ... --json   # 机器可读

口径：
    接触 = 所有记录的 reached 之和
    留联系 = leads 之和
    成交 = deals 之和
    转化率 = 成交 / 接触（接触为 0 时不计算，写 —）
"""

import argparse
import csv
import json
from collections import defaultdict
from datetime import date


def load_points(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_notes(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise SystemExit("记录表应为 JSON 数组，每个元素是一条到访记录")
    return data


def rate(deals, reached):
    if not reached:
        return "—"
    return f"{deals / reached * 100:.1f}%"


def aggregate(notes, key):
    agg = defaultdict(lambda: {"visits": 0, "reached": 0, "leads": 0, "deals": 0, "last": ""})
    for n in notes:
        k = n.get(key) or "未标注"
        a = agg[k]
        a["visits"] += 1
        a["reached"] += int(n.get("reached") or 0)
        a["leads"] += int(n.get("leads") or 0)
        a["deals"] += int(n.get("deals") or 0)
        d = n.get("date") or ""
        if d > a["last"]:
            a["last"] = d
    return agg


def table(title, agg):
    lines = [f"### {title}", "", "| 对象 | 次数 | 接触 | 留联系 | 成交 | 转化率 | 最近一次 |",
             "|---|---|---|---|---|---|---|"]
    for k in sorted(agg):
        a = agg[k]
        lines.append(f"| {k} | {a['visits']} | {a['reached']} | {a['leads']} | {a['deals']} | "
                     f"{rate(a['deals'], a['reached'])} | {a['last'] or '—'} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--points", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--json", action="store_true", help="输出 JSON 而不是表格")
    ap.add_argument("--stale-days", type=int, default=14,
                    help="超过多少天没到访算失联，默认 14")
    args = ap.parse_args()

    points = load_points(args.points)
    notes = load_notes(args.notes)
    names = {(p.get("id") or "").strip(): (p.get("name") or "").strip() for p in points}

    # 记录里出现了点位表没有的 id，说明有人填错了编号，先报出来
    unknown = sorted({(n.get("point_id") or "") for n in notes} - set(names))
    unknown = [u for u in unknown if u]

    by_point = aggregate(notes, "point_id")
    by_owner = aggregate(notes, "owner")

    reached = sum(int(n.get("reached") or 0) for n in notes)
    leads = sum(int(n.get("leads") or 0) for n in notes)
    deals = sum(int(n.get("deals") or 0) for n in notes)

    stale = []
    today = date.today()
    for p in points:
        d = (p.get("last_visit") or "").strip()
        st = (p.get("status") or "").strip()
        if not d or st == "未接触":
            continue
        try:
            gap = (today - date.fromisoformat(d)).days
        except ValueError:
            continue
        if gap > args.stale_days:
            stale.append((p.get("id", ""), names.get(p.get("id", ""), ""), gap))

    if args.json:
        out = {
            "total": {"records": len(notes), "reached": reached, "leads": leads, "deals": deals,
                      "convert": rate(deals, reached)},
            "by_point": {k: dict(v) for k, v in by_point.items()},
            "by_owner": {k: dict(v) for k, v in by_owner.items()},
            "unknown_point_ids": unknown,
            "stale_points": [{"id": i, "name": n, "days": g} for i, n, g in stale],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print("# 漏斗\n")
    print(f"记录 {len(notes)} 条，接触 {reached}，留联系 {leads}，成交 {deals}，"
          f"整体转化率 {rate(deals, reached)}\n")
    print(table("按点位", by_point) + "\n")
    print(table("按人", by_owner) + "\n")
    if unknown:
        print("点位编号对不上点位表：" + "、".join(unknown) + "（先修数据，别急着看数）\n")
    if stale:
        print(f"超过 {args.stale_days} 天没到访、状态却不是未接触：")
        for i, n, g in stale:
            print(f"  {i} {n}：{g} 天")
        print("")


if __name__ == "__main__":
    main()
