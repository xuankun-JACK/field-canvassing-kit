#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把点位表渲染成一张本地可打开的点位图。

刻意不接任何底图服务：底图有自己的授权、坐标系和配额，属于你要自己决定的部分。
这里只保证一件事——点位之间的相对位置和状态，能在一屏上看见。

用法：
    python3 scripts/build_map.py --points samples/points.example.csv --out map.html

想看真地图：在生成的 HTML 里，把 <svg> 外面套一层你的地图容器（Leaflet、地图 API
的 canvas 都行），把 _project() 换成地图自带的坐标转换函数即可。接口就这一个。
"""

import argparse
import csv
import html

STATUS_COLOR = {
    "未接触": "#9AA5B1",
    "已接触": "#2E6BE6",
    "有进展": "#E0A32E",
    "重点跟进": "#D9534F",
}
TYPE_SHAPE = {"门店": "rect", "社区": "circle", "商圈": "tri", "园区": "diamond"}
W, H, PAD = 1000, 640, 60


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        try:
            out.append({
                "id": (r.get("id") or "").strip(),
                "name": (r.get("name") or "").strip(),
                "type": (r.get("type") or "").strip(),
                "lng": float(r["lng"]),
                "lat": float(r["lat"]),
                "owner": (r.get("owner") or "").strip(),
                "status": (r.get("status") or "未接触").strip(),
            })
        except (KeyError, ValueError):
            continue
    return out


def project(points):
    """经纬度 -> 画布像素。只做线性映射，够看相对位置，不是投影算法。"""
    if not points:
        return points
    xs = [p["lng"] for p in points]
    ys = [p["lat"] for p in points]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span_x = (x1 - x0) or 1e-6
    span_y = (y1 - y0) or 1e-6
    for p in points:
        p["px"] = PAD + (p["lng"] - x0) / span_x * (W - 2 * PAD)
        p["py"] = H - PAD - (p["lat"] - y0) / span_y * (H - 2 * PAD)  # 纬度越大越靠上
    return points


def shape(p):
    color = STATUS_COLOR.get(p["status"], "#9AA5B1")
    x, y = p["px"], p["py"]
    kind = TYPE_SHAPE.get(p["type"], "circle")
    if kind == "rect":
        el = f'<rect x="{x-9:.1f}" y="{y-9:.1f}" width="18" height="18" rx="3" fill="{color}"/>'
    elif kind == "tri":
        el = (f'<polygon points="{x:.1f},{y-11:.1f} {x+10:.1f},{y+8:.1f} '
              f'{x-10:.1f},{y+8:.1f}" fill="{color}"/>')
    elif kind == "diamond":
        el = (f'<polygon points="{x:.1f},{y-11:.1f} {x+11:.1f},{y:.1f} '
              f'{x:.1f},{y+11:.1f} {x-11:.1f},{y:.1f}" fill="{color}"/>')
    else:
        el = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{color}"/>'
    label = html.escape(p["id"])
    return (f'<g><title>{label} {html.escape(p["name"])} · {html.escape(p["status"])}'
            f'{" · " + html.escape(p["owner"]) if p["owner"] else ""}</title>{el}'
            f'<text x="{x:.1f}" y="{y+26:.1f}" text-anchor="middle" font-size="13" '
            f'fill="#5B6068">{label}</text></g>')


def render(points):
    body = "\n".join(shape(p) for p in points)
    legend = "".join(
        f'<span class="lg"><i style="background:{c}"></i>{html.escape(s)}</span>'
        for s, c in STATUS_COLOR.items()
    )
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<title>点位图</title>
<style>
  body{{margin:0;background:#F7F5F1;color:#20242B;
       font-family:"PingFang SC","Helvetica Neue",system-ui,sans-serif;}}
  .wrap{{max-width:1060px;margin:32px auto;padding:0 20px;}}
  h1{{font-size:22px;font-weight:600;margin:0 0 6px;}}
  .sub{{color:#8E8A81;font-size:14px;margin-bottom:18px;}}
  .card{{background:#fff;border-radius:14px;box-shadow:0 6px 24px rgba(0,0,0,.06);padding:16px;}}
  .lg{{display:inline-flex;align-items:center;gap:7px;margin-right:22px;font-size:14px;color:#5B6068;}}
  .lg i{{width:13px;height:13px;border-radius:4px;display:inline-block;}}
  .foot{{color:#A9A49B;font-size:13px;margin-top:14px;line-height:1.7;}}
</style></head><body>
<div class="wrap">
  <h1>点位图</h1>
  <div class="sub">点位 {len(points)} 个 · 颜色是状态 · 形状是类型 · 无底图（底图自己接）</div>
  <div class="card">
    <svg viewBox="0 0 {W} {H}" width="100%" height="auto">
      <defs><pattern id="g" width="50" height="50" patternUnits="userSpaceOnUse">
        <path d="M50 0H0V50" fill="none" stroke="#EFECE5" stroke-width="1"/></pattern></defs>
      <rect width="{W}" height="{H}" fill="#FBFAF7"/>
      <rect width="{W}" height="{H}" fill="url(#g)"/>
      {body}
    </svg>
    <div style="margin-top:14px">{legend}</div>
  </div>
  <div class="foot">
    这张图只画相对位置，不做投影校正。<br>
    要换成真地图：把 svg 套进你自己的地图容器，把 project() 换成地图的坐标转换函数。
  </div>
</div>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--points", required=True)
    ap.add_argument("--out", default="map.html")
    args = ap.parse_args()
    points = project(load(args.points))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(points))
    print(f"已生成 {args.out}（{len(points)} 个点位）。用浏览器双击打开。")


if __name__ == "__main__":
    main()
