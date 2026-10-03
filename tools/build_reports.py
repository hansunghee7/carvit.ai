#!/usr/bin/env python3
"""테크리포트 연결 생성기(2026-10-03 탐, 대장 N123). 정본은 reports.json 하나다.

왜: 글 한 편을 발행할 때마다 목록 카드(2쪽), 모든 페이지 꼬리 메뉴, 사이트맵, 이전·다음 글 링크를 손으로 고쳐야 했다.
    이 스크립트가 reports.json에서 그 연결을 전부 만든다. 글 본문(tech-report/<slug>/index.html, ko/ 같은 곳)은 사람이 쓴다.

사용:
  python tools/build_reports.py            reports.json에서 연결을 다시 만든다(바뀐 파일만 쓴다)
  python tools/build_reports.py --check    정본과 파일이 다르면 실패(종료 코드 1). 깃허브 검사가 PR마다 돈다
  python tools/build_reports.py --next     다음 글 번호와 주소 이름 안내

새 글 추가 순서: (1) --next로 번호 확인 (2) reports.json에 항목 추가 (3) 글 쪽 tech-report/<slug>/index.html, ko/tech-report/<slug>/index.html 작성
  (4) python tools/build_reports.py (5) 변경을 커밋. 번호는 reports.json에서 자동으로 다음 번호를 받으므로 서로 맞출 필요가 없다(같은 번호를 두 PR이 쓰면 두 번째 PR에서 충돌로 드러난다).

생성하는 곳(표시자 <!--rp:...-->가 있는 곳만 건드린다):
  - tech-report/index.html, ko/tech-report/index.html: 카드 목록(최신 번호가 위)
  - 모든 .html의 꼬리 메뉴 안 테크리포트 링크
  - 각 글 맨 아래 이전·다음 글 링크(nav.pn 안쪽)
  - sitemap.xml의 테크리포트 항목(<!--rp:sitemap--> 블록)과 목록 페이지의 lastmod
reports.json 문자열은 HTML에 그대로 들어가므로 &amp; 같은 표기를 직접 쓴다.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'reports.json'
LANG = {
    'en': dict(base='', label='Tech Report', ver='Version', btn='Read more', prev='Previous', next='Next', index_title='Tech Report'),
    'ko': dict(base='/ko', label='테크리포트', ver='v', btn='자세히 보기', prev='이전 글', next='다음 글', index_title='테크리포트'),
}


def load():
    d = json.loads(DATA.read_text(encoding='utf-8'))
    ns = [r['n'] for r in d['reports']]
    if len(set(ns)) != len(ns):
        raise SystemExit(f'reports.json: 번호가 겹칩니다 {sorted(ns)}')
    return sorted(d['reports'], key=lambda r: -r['n'])


def rd(p):
    # Path.read_text(newline=)은 파이썬 3.13부터라 3.12에서도 돌도록 open을 쓴다
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def nl_of(s):
    return '\r\n' if '\r\n' in s else '\n'


def card(r, lang):
    L = LANG[lang]
    note_ver = f'Version {r["version"]}' if lang == 'en' else f'v{r["version"]}'
    note = f'{r["date"]} · {r["field"][lang]} · {L["label"]} {r["n"]} · {note_ver} · {r["author"][lang]}'
    return (f'  <div class="card report"><p class="note">{note}</p><h2>{r["card_title"][lang]}</h2><p class="lead">{r["summary"][lang]}</p>'
            f'<div class="actions"><a class="btn" href="{L["base"]}/tech-report/{r["slug"]}/">{L["btn"]}</a></div></div>')


def sub_between(s, start, end, body, nl, indent=''):
    """표시자 사이 내용을 body로 바꾼다. 표시자가 없으면 None."""
    i, j = s.find(start), s.find(end)
    if i < 0 or j < 0 or j < i:
        return None
    return s[:i + len(start)] + nl + body + nl + indent + s[j:]


def build_outputs(reports):
    out = {}  # 경로 → 새 내용
    latest = max(r['date'] for r in reports)
    files = [f for f in subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True, encoding='utf-8').split('\n') if f.endswith('.html')]
    # 1) 목록 카드 + 꼬리 메뉴
    for f in files:
        p = ROOT / f
        s = rd(p)
        orig = s
        nl = nl_of(s)
        lang = 'ko' if f.startswith('ko/') else 'en'
        L = LANG[lang]
        if f in ('tech-report/index.html', 'ko/tech-report/index.html'):
            body = nl.join(card(r, lang) for r in reports)
            t = sub_between(s, '<!--rp:cards-->', '<!--/rp:cards-->', body, nl, '  ')
            if t is None:
                raise SystemExit(f'{f}: <!--rp:cards--> 표시자가 없습니다')
            s = t
        if '<!--rp:foot-->' in s:
            links = ''.join(f'<a href="{L["base"]}/tech-report/{r["slug"]}/">{L["label"]} {r["n"]}</a>' for r in reports)
            i, j = s.index('<!--rp:foot-->'), s.index('<!--/rp:foot-->')
            s = s[:i] + '<!--rp:foot-->' + links + s[j:]
        # 2) 글 맨 아래 이전·다음 글
        m = re.match(r'(ko/)?tech-report/([^/]+)/index\.html$', f)
        if m:
            slug = m.group(2)
            cur = next((r for r in reports if r['slug'] == slug), None)
            if cur:
                prev = next((r for r in reports if r['n'] == cur['n'] - 1), None)
                nxt = next((r for r in reports if r['n'] == cur['n'] + 1), None)
                parts = []
                if prev:
                    parts.append(f'<a class="link-btn" href="{L["base"]}/tech-report/{prev["slug"]}/">← {L["prev"]}: {L["label"]} {prev["n"]}</a><span class="pn-t">{prev["nav_title"][lang]}</span>')
                if nxt:
                    parts.append(f'<a class="link-btn" href="{L["base"]}/tech-report/{nxt["slug"]}/">{L["next"]}: {L["label"]} {nxt["n"]} →</a><span class="pn-t">{nxt["nav_title"][lang]}</span>')
                mm = re.search(r'(<nav class="pn"[^>]*>)(.*?)(</nav>)', s, re.S)
                if not mm:
                    raise SystemExit(f'{f}: <nav class="pn"> 이 없습니다')
                s = s[:mm.end(1)] + ''.join(parts) + s[mm.start(3):]
        if s != orig:
            out[f] = s
    # 3) 사이트맵
    sp = ROOT / 'sitemap.xml'
    s = rd(sp)
    nl = nl_of(s)
    blocks = []
    for r in reports:
        for lang in ('en', 'ko'):
            base = LANG[lang]['base']
            blocks.append(nl.join([
                '  <url>', f'    <loc>https://carvit.ai{base}/tech-report/{r["slug"]}/</loc>', f'    <lastmod>{r["date"]}</lastmod>',
                f'    <xhtml:link rel="alternate" hreflang="en" href="https://carvit.ai/tech-report/{r["slug"]}/"/>',
                f'    <xhtml:link rel="alternate" hreflang="ko" href="https://carvit.ai/ko/tech-report/{r["slug"]}/"/>',
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="https://carvit.ai/tech-report/{r["slug"]}/"/>', '  </url>']))
    block = '  <!--rp:sitemap-->' + nl + nl.join(blocks) + nl + '  <!--/rp:sitemap-->'
    slugs = '|'.join(re.escape(r['slug']) for r in reports)
    s2 = re.sub(r'  <!--rp:sitemap-->.*?<!--/rp:sitemap-->', lambda _: '@@RP@@', s, flags=re.S)
    if '@@RP@@' not in s2:
        # 처음: 옛 항목 제거 후 </urlset> 앞에 표시자 블록 삽입
        s2 = re.sub(rf'[ \t]*<url>\s*<loc>https://carvit\.ai(?:/ko)?/tech-report/(?:{slugs})/</loc>.*?</url>[ \t]*\r?\n', '', s, flags=re.S)
        s2 = s2.replace('</urlset>', '@@RP@@' + nl + '</urlset>')
    s2 = s2.replace('@@RP@@', block)
    # 목록 페이지 lastmod = 가장 최근 글 날짜
    for loc in ('https://carvit.ai/tech-report/', 'https://carvit.ai/ko/tech-report/'):
        s2 = re.sub(rf'(<loc>{re.escape(loc)}</loc>\s*<lastmod>)[^<]*', lambda m: m.group(1) + latest, s2, count=1)
    if s2 != s:
        out['sitemap.xml'] = s2
    return out


def main():
    args = sys.argv[1:]
    reports = load()
    if '--next' in args:
        n = max(r['n'] for r in reports) + 1
        print(f'다음 글 번호: {n}  (영문 tech-report/<slug>/, 한글 ko/tech-report/<slug>/ 를 만들고 reports.json에 항목 추가)')
        return 0
    out = build_outputs(reports)
    if '--check' in args:
        if out:
            print('정본(reports.json)과 다른 파일이 있습니다. python tools/build_reports.py 를 실행해 커밋하세요:')
            for f in sorted(out):
                print('  ', f)
            return 1
        print('정본과 일치합니다.')
        return 0
    for f, s in out.items():
        (ROOT / f).write_text(s, encoding='utf-8', newline='')
    print(f'갱신 {len(out)}개' + ((': ' + ', '.join(sorted(out))) if out and len(out) <= 6 else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
