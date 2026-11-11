#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""点位表校验。

只回答一个问题：这张表能不能进下一步。不取数，不联网。

用法：
    python3 scripts/points_schema.py samples/points.example.csv

校验项：
    1 表头是否含全部必需字段
    2 必需字段是否有空值
    3 status 是否在四个词之内
    4 lng / lat 是否为合法数值且在合理范围
    5 id 是否唯一
    6 last_visit 是否为 YYYY-MM-DD
"""

import csv
import sys
import datetime

FIELDS = ["id", "name", "type", "lng", "lat", "owner", "status", "last_visit", "visits"]
REQUIRED = ["id", "name", "lng", "lat", "status"]
STATUS = ["未接触", "已接触", "有进展", "重点跟进"]


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = list(reader)
    return header, rows


def validate(header, rows):
    errors = []
    missing = [c for c in REQUIRED if c not in header]
    if missing:
        errors.append(f"缺少必需列：{', '.join(missing)}")
    extra = [c for c in header if c not in FIELDS]
    if extra:
        errors.append(f"多出未定义的列（不影响运行，确认是否需要）：{', '.join(extra)}")

    seen = {}
    for i, r in enumerate(rows, start=2):  # 第 1 行是表头
        rid = (r.get("id") or "").strip()
        if not rid:
            errors.append(f"第 {i} 行：id 为空")
            continue
        if rid in seen:
            errors.append(f"第 {i} 行：id {rid} 与第 {seen[rid]} 行重复")
        seen[rid] = i

        for col in REQUIRED:
            if col in header and not (r.get(col) or "").strip():
                errors.append(f"第 {i} 行 {rid}：{col} 为空")

        st = (r.get("status") or "").strip()
        if st and st not in STATUS:
            errors.append(f"第 {i} 行 {rid}：status「{st}」不在词表内（{'/'.join(STATUS)}）")

        for col, lo, hi in (("lng", 70, 140), ("lat", 0, 60)):
            v = (r.get(col) or "").strip()
            if not v:
                continue
            try:
                num = float(v)
            except ValueError:
                errors.append(f"第 {i} 行 {rid}：{col} 不是数字")
                continue
            if not (lo <= num <= hi):
                errors.append(f"第 {i} 行 {rid}：{col} 取值 {num} 不在合理范围，可能是坐标系写反或误填")

        d = (r.get("last_visit") or "").strip()
        if d:
            try:
                datetime.date.fromisoformat(d)
            except ValueError:
                errors.append(f"第 {i} 行 {rid}：last_visit 应为 YYYY-MM-DD，当前「{d}」")

    return errors


def summary(header, rows):
    counts = {s: 0 for s in STATUS}
    for r in rows:
        st = (r.get("status") or "").strip()
        if st in counts:
            counts[st] += 1
    lines = [f"共 {len(rows)} 个点位"]
    lines += [f"  {k}：{v}" for k, v in counts.items()]
    owners = sorted({(r.get("owner") or "").strip() for r in rows} - {""})
    if owners:
        lines.append(f"负责人 {len(owners)} 人：{'、'.join(owners)}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    header, rows = load(sys.argv[1])
    errors = validate(header, rows)
    print(summary(header, rows))
    if errors:
        print(f"\n发现 {len(errors)} 处问题：")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print("\n校验通过。")


if __name__ == "__main__":
    main()
