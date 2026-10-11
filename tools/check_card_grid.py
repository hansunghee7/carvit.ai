#!/usr/bin/env python3
"""카드 그리드 칸 크기 균일 검사(검사 공백 G-4, 2026-10-11 지투).

배경: 홈 템플릿 카드가 휴대폰에서 좌우 폭이 달랐고 5번째 카드만 전체 폭이었다(사장님이 보고서 화면에서 발견).
가이드 1.50 ⑤는 가로 넘침만 봐서 이런 불균일을 못 잡았다. 이 검사는 같은 부모 안에서 같은 클래스를 가진 형제가 3개 이상이면
각 폭이 서로 2px 안에서 같은지 본다(display:grid 부모만 본다: 한 줄에 여러 개든 한 칸씩 쌓이든 같은 폭이어야 한다).

사용: python tools/check_card_grid.py   (playwright 필요, 없으면 건너뛰지 않고 실패)
종료 코드 0 = 통과, 1 = 불균일 발견.
"""
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["/", "/ko/", "/ux-mcp/", "/ko/ux-mcp/"]
WIDTHS = [375, 768]
TOL = 2

JS = """
() => {
  const out = [];
  document.querySelectorAll('*').forEach(parent => {
    const groups = {};
    [...parent.children].forEach(c => {
      if (!c.className || typeof c.className !== 'string') return;
      const key = c.tagName + '.' + c.className.trim().split(/\\s+/).sort().join('.');
      (groups[key] = groups[key] || []).push(c);
    });
    for (const [key, els] of Object.entries(groups)) {
      if (els.length < 3) continue;
      const vis = els.filter(e => e.offsetParent !== null);
      if (vis.length < 3) continue;
      const ws = vis.map(e => Math.round(e.getBoundingClientRect().width));
      const display = getComputedStyle(parent).display;
      if (display !== 'grid') continue;  // flex 줄바꿈 칩(tiles 등)은 폭이 제각각이 정상
      out.push({key, ws, display, parent: parent.tagName + (parent.className ? '.' + String(parent.className).trim().split(/\\s+/).join('.') : '')});
    }
  });
  return out;
}
"""


def main():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        bad = []
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w in WIDTHS:
                page = browser.new_page(viewport={"width": w, "height": 900})
                for path in PAGES:
                    page.goto(f"http://127.0.0.1:{port}{path}")
                    for g in page.evaluate(JS):
                        # 카드처럼 보이는 묶음만: 클래스에 card/plan 이 들어간 것
                        if not any(k in g["key"].lower() for k in ("card", "plan")):
                            continue
                        if max(g["ws"]) - min(g["ws"]) > TOL:
                            bad.append(f"{path} @{w}px {g['parent']} > {g['key']} 폭 {g['ws']}")
            browser.close()
        srv.shutdown()
    if bad:
        print("FAIL 카드 폭이 균일하지 않습니다:")
        for b in bad:
            print("  -", b)
        return 1
    print("OK 카드 그리드 칸 크기 균일")
    return 0


if __name__ == "__main__":
    sys.exit(main())
