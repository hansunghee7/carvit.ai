#!/usr/bin/env python3
"""가이드↔라이브 화면 대조(2026-10-15, 탐 컨텍스트 감수 '가이드 어긋남 감지' 갈래).

carvit.ai 사이트맵의 모든 화면과 앱 공개 화면을 PC(1440)·휴대폰(390)으로 열어, Carvit UX
가이드 값과 실제 계산된 값(getComputedStyle)이 다른 곳을 목록으로 낸다. 값은 가이드 절에서
옮겨 적고 절 번호를 같이 단다(가이드가 바뀌면 이 표를 같이 고친다). 판정이 아니라 목록이다:
사람이 근거 수치를 보고 고칠지 정한다.

사용법:
    uv run --python 3.11 --with playwright==1.62.0 python tools/guide_live_audit.py \
        [--base https://carvit.ai] [--out C:/work/_ops/context_audit]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

WIDTHS = (1440, 390)
APP_PAGES = ["https://mcp.carvit.ai/login"]

# 가이드 값(절 번호). 휴대폰 = 폭 760 이하.
G = {
    "hdr_h": {"pc": 64, "phone": 56, "sec": "1.39"},
    "hdr_pad": {"pc": 32, "phone": 24, "sec": "1.39"},
    "logo_fs": {"pc": 19, "phone": 19, "sec": "1.39"},
    "tap_min": {"phone": 44, "sec": "1.34"},
    "home_sec": {"pc": 60, "phone": 60, "sec": "1.37 ⑪"},
    "text_sect": {"pc": 80, "phone": 56, "sec": "1.42 ⑨"},
    "pagehead": {"pc": (96, 48), "sec": "1.42 ⑨"},
    "post_fs": {"pc": 17, "phone": 16, "sec": "1.42 ①"},
}

JS = r"""
(menu) => {
  const vw = innerWidth, out = {};
  const px = v => Math.round(parseFloat(v) * 10) / 10;
  // 머리: 사이트 메뉴 첫 항목(/ux-mcp/) 링크를 품은, 화면 맨 위에 붙은 가장 가까운 넓은 조상
  const first = [...document.querySelectorAll('a[href$="/ux-mcp/"]')].find(a => a.getBoundingClientRect().top < 120);
  let bar = null;
  if (first) {
    for (let e = first.parentElement; e && e !== document.body; e = e.parentElement) {
      const r = e.getBoundingClientRect();
      if (r.width >= vw - 2 && r.top <= 1) { bar = e; break; }
    }
  }
  const logo = [...document.querySelectorAll('a')].find(a => /^\s*Carvit\s*$/.test(a.textContent) && a.getBoundingClientRect().top < 80);
  if (bar) {
    out.hdr_h = px(bar.getBoundingClientRect().height);
    if (logo) out.hdr_pad = px(logo.getBoundingClientRect().left - bar.getBoundingClientRect().left);
  }
  if (logo) out.logo_fs = px(getComputedStyle(logo).fontSize);
  // 메뉴 순서·이름: 머리 메뉴 묶음(첫 메뉴 링크의 부모) 안에서 언어·로그인 링크를 뺀 메뉴 링크만
  const menuLinks = first ? [...first.parentElement.querySelectorAll('a')].filter(a =>
    !a.matches('.lang,.login,.cv-lang') && !/^(English|한국어|Log in|로그인)$/.test(a.textContent.trim()) &&
    menu.some(m => (a.getAttribute('href') || '').endsWith(m.path))) : [];
  out.menu_paths = menuLinks.map(a => (menu.find(m => a.getAttribute('href').endsWith(m.path)) || {}).path);
  out.menu_texts = menuLinks.map(a => a.textContent.trim());
  // 언어 전환 링크 수(보이는 것만)
  out.lang_links = [...document.querySelectorAll('a')].filter(a => /^(English|한국어)$/.test(a.textContent.trim()))
    .filter(a => { const r = a.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).length;
  out.body_class = document.body.className;
  out.word_break = getComputedStyle(document.body).wordBreak;
  out.overflow = document.documentElement.scrollWidth - innerWidth;
  out.simplifier = /simplifier|심플리파이어/i.test(document.body.innerText);
  const pads = sel => [...document.querySelectorAll(sel)].filter(e => e.getBoundingClientRect().height > 0)
    .map(e => [px(getComputedStyle(e).paddingTop), px(getComputedStyle(e).paddingBottom)]);
  out.home_sec = pads('.sec, .prod, .stats');
  out.text_sect = pads('.text-page .sect, .text-page .cta-band');
  out.pagehead = pads('.text-page .pagehead');
  out.post_fs = [...new Set([...document.querySelectorAll('.post > p, .post > ul > li, .post > ol > li')].map(e => px(getComputedStyle(e).fontSize)))];
  // 휴대폰 누르는 영역(1.34: 480 이하 nav a·.btn 높이 44 이상), 보이는 것만
  if (vw <= 480) {
    out.small_taps = [...document.querySelectorAll('nav a, .btn')].filter(a => {
      const r = a.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.height < 44; })
      .slice(0, 8).map(a => (a.textContent.trim().slice(0, 20) || a.className) + ' ' + px(a.getBoundingClientRect().height));
  }
  // 제품 이름·짧은 괄호가 두 줄로 쪼개졌는지(1.34)
  const split = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const p = n.parentElement;
    if (!p || ['SCRIPT','STYLE','NOSCRIPT'].includes(p.tagName) || p.closest('.nowrap,pre,code,.pane,.app')) continue;
    for (const re of [/Claude Code/g, /Carvit Pass/g, /Carvit UX/g]) {
      re.lastIndex = 0; let m;
      while ((m = re.exec(n.nodeValue))) {
        const r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
        const tops = new Set([...r.getClientRects()].filter(x => x.width > 0).map(x => Math.round(x.top)));
        if (tops.size > 1) split.push(m[0]);
      }
    }
  }
  out.split_names = split;
  return out;
}
"""


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (guide_live_audit)"})  # 기본 UA는 Cloudflare가 403
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")


def sitemap_urls(base: str) -> list[str]:
    xml = _get(base + "/sitemap.xml")
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def menu_items(base: str) -> list[dict]:
    return json.loads(_get(base + "/menu.json"))["items"]


def check(url: str, w: int, m: dict, menu: list[dict]) -> list[dict]:
    dev = "pc" if w > 760 else "phone"
    ko = "/ko/" in url  # 앱은 브라우저 언어를 따르고 실측 브라우저는 en-US
    found = []

    def add(rule, sec, want, got, fix):
        found.append({"url": url, "width": w, "rule": rule, "section": sec, "want": want, "got": got, "fix": fix})

    for k in ("hdr_h", "hdr_pad", "logo_fs"):
        want = G[k][dev]
        if k in m and abs(m[k] - want) > 0.5:
            add(k, G[k]["sec"], want, m[k], {"hdr_h": "머리 높이", "hdr_pad": "머리 좌우 여백(로고 왼쪽 끝)", "logo_fs": "로고 글자 크기"}[k] + f"을 {want}px로")
    if "hdr_h" not in m:
        add("hdr_found", "1.39", "머리 막대", "못 찾음", "머리 구조 확인(메뉴 첫 링크 /ux-mcp/를 품은 맨 위 막대가 없음)")
    want_paths = [i["path"] for i in menu]
    if m["menu_paths"] and m["menu_paths"] != want_paths:
        add("menu_order", "1.39", want_paths, m["menu_paths"], "메뉴 순서·항목을 menu.json과 같게")
    want_texts = [i["ko" if ko else "en"] for i in menu]
    if m["menu_texts"] and m["menu_texts"] != want_texts:
        add("menu_text", "1.39", want_texts, m["menu_texts"], "메뉴 이름을 화면 언어에 맞게")
    if m["lang_links"] > 1:
        add("lang_once", "1.34", 1, m["lang_links"], "언어 전환 링크는 한 화면에 한 번만")
    if m["word_break"] != "keep-all":
        add("keep_all", "1.34", "keep-all", m["word_break"], "body에 word-break:keep-all")
    if m["overflow"] > 0:
        add("overflow", "1.34", 0, m["overflow"], "가로 스크롤이 생기지 않게")
    if m["simplifier"]:
        add("no_simplifier", "1.34", "없음", "있음", "회사 이름 Simplifier·심플리파이어를 지우기")
    if m["split_names"]:
        add("nowrap_names", "1.34", "한 줄", sorted(set(m["split_names"])), "제품 이름을 .nowrap으로 감싸기")
    if m.get("small_taps"):
        add("tap_44", "1.34", ">=44px", m["small_taps"], "누르는 영역 높이 44px 이상")
    if "text-page" not in m["body_class"] and m["home_sec"]:
        want = G["home_sec"][dev]
        bad = [p for p in m["home_sec"] if p[0] != want or p[1] not in (want, 200)]  # .final 아래 200은 하단 띠 값
        if bad:
            add("home_sec", G["home_sec"]["sec"], want, bad, f"홈 섹션 위아래 {want}px")
    if m["text_sect"]:
        want = G["text_sect"][dev]
        bad = [p for p in m["text_sect"] if p != [want, want]]
        if bad:
            add("text_sect", G["text_sect"]["sec"], want, bad, f"글 페이지 섹션 위아래 {want}px")
    if m["pagehead"] and dev == "pc":
        want = list(G["pagehead"]["pc"])
        bad = [p for p in m["pagehead"] if p != want]
        if bad:
            add("pagehead", G["pagehead"]["sec"], want, bad, "글 머리 위 96·아래 48")
    if m["post_fs"]:
        want = G["post_fs"][dev]
        if any(abs(f - want) > 0.5 for f in m["post_fs"]):
            add("post_fs", G["post_fs"]["sec"], want, m["post_fs"], f"글 본문 {want}px")
    return found


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://carvit.ai")
    ap.add_argument("--out", default="C:/work/_ops/context_audit")
    a = ap.parse_args()
    menu = menu_items(a.base)
    urls = [u.replace("https://carvit.ai", a.base) for u in sitemap_urls(a.base)] + APP_PAGES  # --base가 로컬이면 사이트맵 주소도 로컬로
    findings, measured = [], 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for url in urls:
            for w in WIDTHS:
                c = b.new_context(viewport={"width": w, "height": 900}, locale="ko-KR" if "/ko/" in url else "en-US")
                pg = c.new_page()
                pg.goto(url, wait_until="load", timeout=60000)
                pg.wait_for_timeout(500)
                findings += check(url, w, pg.evaluate(JS, menu), menu)
                measured += 1
                c.close()
        b.close()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    day = dt.date.today().strftime("%Y%m%d")
    (out / f"guide_diff_{day}.json").write_text(json.dumps(findings, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# 가이드↔라이브 화면 대조 {day}", "",
             f"- 대상: {len(urls)}개 화면 × {len(WIDTHS)}폭 = {measured}회 실측(carvit.ai 사이트맵 + 앱 공개 화면)",
             f"- 어긋남: {len(findings)}건 (규칙별 {dict(sorted(_count(findings).items()))})",
             "- 판정이 아니라 목록이다. 근거 수치를 보고 고칠지 정한다. 도구: carvit.ai tools/guide_live_audit.py", ""]
    for f in findings:
        lines.append(f"- [{f['rule']}] {f['url']} @{f['width']} 가이드 {f['section']}: 기대 {f['want']} / 실측 {f['got']} → 제안: {f['fix']}")
    (out / f"guide_diff_{day}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:5]))


def _count(fs):
    c = {}
    for f in fs:
        c[f["rule"]] = c.get(f["rule"], 0) + 1
    return c


if __name__ == "__main__":
    main()
