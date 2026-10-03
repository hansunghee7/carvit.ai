#!/usr/bin/env python3
"""머리 메뉴를 정본 목록 menu.json에서 모든 페이지에 채운다(2026-10-03 탐, 대장 N127, 지투 요청).

정본: menu.json  {version:1, items:[{id, ko, en, path}]}  순서 = 배열 순서, path는 영어 기준(한국어는 /ko 가 앞에 붙음).
앱(mcp.carvit.ai)도 같은 목록을 읽는다: https://carvit.ai/menu.json, 사본 해시 한 줄 파일 https://carvit.ai/menu.sha256
  해시 = sha256( 정규화 JSON ), 정규화 = json.dumps(menu, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

채우는 곳(표시자가 있거나, 아래 구조에 해당하는 곳만 건드린다):
  - 서브 페이지 머리 <div class="links"> ... <a class="lang"  : 표시자 <!--mn:head-->...<!--/mn:head--> 안쪽(처음 실행 때 표시자를 심는다)
  - 홈 머리 <div class="menu">...</div> 와 모바일 시트 <div class="sheet" id="sheet">...<a ... hreflang=...>
  - menu.sha256

사용: python tools/build_menu.py          다시 만들어 파일에 쓴다
      python tools/build_menu.py --check  파일이 정본과 같은지만 검사(다르면 종료코드 1, 깃허브 menu-check가 쓴다)
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NL = chr(10)


def load():
    m = json.loads((ROOT / 'menu.json').read_text(encoding='utf-8'))
    assert m.get('version') == 1 and m.get('items'), 'menu.json 형식 오류(version 1, items 필요)'
    return m


def digest(m):
    return hashlib.sha256(json.dumps(m, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()


def page_url(rel):
    u = '/' + rel.replace('index.html', '')
    return u


def lang_of(rel):
    return 'ko' if rel.startswith('ko/') else 'en'


def links_sub(m, lang, url):
    base = '/ko' if lang == 'ko' else ''
    out = []
    for it in m['items']:
        href = base + it['path']
        cur = ' aria-current="page"' if url.startswith(href) else ''
        out.append(f'<a href="{href}"{cur}><span class="nowrap">{it[lang]}</span></a>')
    return ''.join(out)


def links_home(m, lang):
    base = '/ko' if lang == 'ko' else ''
    return ''.join(f'<a href="{base + it["path"]}">{it[lang]}</a>' for it in m['items'])


def rewrite(rel, s, m):
    lang, url = lang_of(rel), page_url(rel)
    # 서브 페이지 머리
    pat = re.compile(r'(<nav class="top"[^>]*>.*?<div class="links">)(.*?)(<a class="lang")', re.S)
    mm = pat.search(s)
    if mm:
        new = '<!--mn:head-->' + links_sub(m, lang, url) + '<!--/mn:head-->'
        s = s[:mm.start(2)] + new + s[mm.end(2):]
        # 서브 페이지 모바일 시트(같은 목록, 같은 활성 표시)
        pat2 = re.compile(r'(<div class="sheet" id="sheet">)(.*?)(<a class="lang")', re.S)
        m2 = pat2.search(s)
        if m2:
            new2 = '<!--mn:sheet-->' + links_sub(m, lang, url) + '<!--/mn:sheet-->'
            s = s[:m2.start(2)] + new2 + s[m2.end(2):]
    # 홈 머리
    pat = re.compile(r'(<div class="menu">)(.*?)(</div>)', re.S)
    mm = pat.search(s)
    if mm and '<nav class="nav"' in s:
        new = '<!--mn:head-->' + links_home(m, lang) + '<!--/mn:head-->'
        s = s[:mm.start(2)] + new + s[mm.end(2):]
        # 모바일 시트: 메뉴 링크들 + (언어 링크는 그대로)
        pat = re.compile(r'(<div class="sheet" id="sheet">)(.*?)(<a [^>]*hreflang=)', re.S)
        mm = pat.search(s)
        if mm:
            new = '<!--mn:sheet-->' + links_home(m, lang) + '<!--/mn:sheet-->'
            s = s[:mm.start(2)] + new + s[mm.end(2):]
    return s


def main():
    check = '--check' in sys.argv
    m = load()
    changed = []
    for p in sorted(ROOT.rglob('*.html')):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(('assets/', '.git', 'node_modules')) or rel.startswith('google'):
            continue
        raw = p.read_bytes().decode('utf-8')
        crlf = chr(13) + NL in raw
        s = raw.replace(chr(13) + NL, NL)
        t = rewrite(rel, s, m)
        if t != s:
            changed.append(rel)
            if not check:
                p.write_bytes((t.replace(NL, chr(13) + NL) if crlf else t).encode('utf-8'))
    sha = ROOT / 'menu.sha256'
    want = digest(m) + NL
    if not sha.exists() or sha.read_text(encoding='utf-8') != want:
        changed.append('menu.sha256')
        if not check:
            sha.write_text(want, encoding='utf-8')
    if check:
        if changed:
            print('menu 정본과 어긋난 파일:', ', '.join(changed))
            print('로컬에서 python tools/build_menu.py 를 돌려 바뀐 파일을 같이 커밋하세요.')
            sys.exit(1)
        print('menu 검사 통과')
    else:
        print(f'menu 갱신 {len(changed)}개:', ', '.join(changed) if changed else '(변경 없음)')


if __name__ == '__main__':
    main()
