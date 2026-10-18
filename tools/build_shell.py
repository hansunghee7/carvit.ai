#!/usr/bin/env python3
"""머리(상단 메뉴)와 꼬리(footer)를 조각 파일 한 곳에서 모든 페이지에 채운다(2026-10-18 지투, build_menu.py와 같은 방식).

정본: partials/<구역>.<종류>.<언어>.html   언어 = en | ko (ko/ 아래 페이지면 ko)
  꼬리 foot: 종류 = home(홈) | full(제품·팀 열 있는 하위) | short(정책·리포트 하위)
  머리 head: 종류 = home(홈, nav.nav) | sub(하위, div.site-nav)
페이지: <!--shell:foot 종류--><footer ...>...</footer><!--/shell:foot-->
        <!--shell:head 종류--><div class="site-nav">...</div></div><!--/shell:head-->   (홈은 <nav class="nav">...</nav>)

조각 안의 칸(slot): 다른 도구나 페이지가 주인인 구역. 조각을 다시 써도 페이지 값을 그대로 둔다.
  <!--mn:head--><!--/mn:head-->   머리 메뉴 링크(현재 메뉴 aria-current 포함). 주인 build_menu.py(menu.json)
  <!--mn:sheet--><!--/mn:sheet--> 모바일 시트 메뉴 링크. 주인 build_menu.py
  <!--mn:foot--><!--/mn:foot-->   Carvit MCP 열 링크. 주인 build_menu.py(menu.json subnav)
  <!--rp:foot--><!--/rp:foot-->   테크리포트 목록. 주인 build_reports.py(reports.json)
  <!--pg:fine-->기본값<!--/pg:fine-->  맨 아래 한 줄. 페이지에 이 표시자가 있으면 페이지 값(테크리포트 글의 번호·버전·날짜),
                                     없으면 조각의 기본값을 표시자 없이 넣는다.
조각 안의 계산 값: %ALT%  언어 전환 링크 주소. 페이지 경로에서 계산한다(/x/ <-> /ko/x/).

사용: python tools/build_shell.py          다시 만들어 파일에 쓴다(새 페이지는 머리·꼬리를 아무 페이지에서 복사해 두면 된다)
      python tools/build_shell.py --check  페이지 머리·꼬리가 조각과 같은지만 검사(다르면 종료코드 1, 깃허브 menu-check가 쓴다)
      --root <폴더>                         시험용으로 다른 폴더를 대상으로 돈다
고친 뒤에는: python tools/build_shell.py && python tools/build_menu.py && python tools/build_reports.py
"""
import re, sys
from html.parser import HTMLParser
from pathlib import Path

NL = chr(10)
CR = chr(13)
SECTIONS = {
    'head': ('home', 'sub'),
    'foot': ('home', 'full', 'short'),
}
KEEP = ('mn:head', 'mn:sheet', 'mn:foot', 'rp:foot')  # 늘 표시자를 남기고 페이지 값을 쓴다
OVERRIDE = ('pg:fine',)                               # 페이지에 표시자가 있을 때만 페이지 값
SLOT_RE = re.compile(r'<!--((?:mn|rp|pg):[a-z]+)-->(.*?)<!--/\1-->', re.S)
FIND_RE = {  # 표시자가 아직 없는 페이지에서 구역을 찾는 모양
    'foot': re.compile(r'<footer class="(?:foot|bottom)">.*?</footer>', re.S),
    'head': re.compile(r'<div class="site-nav"><div class="page">.*?<div class="sheet" id="sheet">.*?</div>\s*</div></div>'
                       r'|<nav class="nav"[^>]*>.*?<div class="sheet" id="sheet">.*?</div>\s*</nav>', re.S),
}
MCP_COL_RE = re.compile(r'(<div><h5><a href="(?:/ko)?/ux-mcp/">(?:UX MCP|<span class="nowrap">Carvit MCP</span>)</a></h5>)(.*?)(</div>)', re.S)
FINE_RE = re.compile(r'(<p class="fine">)(.*?)(</p>)', re.S)
SKIP = ('assets/', '.git', 'node_modules', '_preview/', 'partials/', 'google')


def block_re(sec):
    return re.compile(rf'<!--shell:{sec} ([a-z]+)-->(.*?)<!--/shell:{sec}-->', re.S)


def lang_of(rel):
    return 'ko' if rel.startswith('ko/') else 'en'


def alt_url(rel):
    """언어 전환 링크: 영어 /x/ <-> 한국어 /ko/x/."""
    u = '/' + rel.replace('index.html', '')
    return u[3:] if rel.startswith('ko/') else '/ko' + u


def read_text(p):
    return p.read_bytes().decode('utf-8').replace(CR + NL, NL)


def load_partials(root):
    parts = {}
    for sec, kinds in SECTIONS.items():
        for k in kinds:
            for lang in ('en', 'ko'):
                p = root / 'partials' / f'{sec}.{k}.{lang}.html'
                parts[(sec, k, lang)] = read_text(p).strip(NL)
    return parts


def strip_markers(s):
    return SLOT_RE.sub(lambda m: m.group(2), s)


class _Canon(HTMLParser):
    """화면에 같은 결과를 내는지 보는 비교용 정규형: 태그·속성(이름 소문자, 정렬)·글자(공백 접기). 주석과 태그 사이 공백은 무시."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []

    def handle_starttag(self, tag, attrs):
        self.out.append(('<', tag, tuple(sorted((k.lower(), v or '') for k, v in attrs))))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.out.append(('>', tag))

    def handle_endtag(self, tag):
        self.out.append(('>', tag))

    def handle_data(self, data):
        t = ' '.join(data.split())
        if t:
            self.out.append(('t', t))


def canon(s):
    c = _Canon()
    c.feed(s)
    c.close()
    return c.out


def page_slots(block, default_fine=None):
    """페이지 구역에서 칸 값을 읽는다. 표시자가 없으면(처음 한 번) 구조로 찾는다."""
    vals = {m.group(1): m.group(2) for m in SLOT_RE.finditer(block)}
    if 'mn:foot' not in vals:
        m = MCP_COL_RE.search(block)
        if m:
            vals['mn:foot'] = m.group(2)
    if 'pg:fine' not in vals and default_fine is not None:
        m = FINE_RE.search(block)
        if m and m.group(2) != default_fine:
            vals['pg:fine'] = m.group(2)
    return vals


def default_of(partial, slot):
    m = re.search(rf'<!--{re.escape(slot)}-->(.*?)<!--/{re.escape(slot)}-->', partial, re.S)
    return m.group(1) if m else None


def render(partial, vals, rel, alt=None):
    def fill(m):
        name, default = m.group(1), m.group(2)
        if name in KEEP:
            return f'<!--{name}-->' + vals.get(name, '') + f'<!--/{name}-->'
        if name in vals:
            return f'<!--{name}-->' + vals[name] + f'<!--/{name}-->'
        return default
    return SLOT_RE.sub(fill, partial).replace('%ALT%', alt if alt is not None else alt_url(rel))


def wrap(sec, kind, body):
    return f'<!--shell:{sec} {kind}-->' + body + f'<!--/shell:{sec}-->'


def rewrite_section(sec, rel, s, parts):
    """구역 하나를 다시 쓴 내용을 돌려준다. 맞는 조각을 못 찾으면 ValueError."""
    lang = lang_of(rel)
    m = block_re(sec).search(s)
    if m:
        kind, block = m.group(1), m.group(2)
        if (sec, kind, lang) not in parts:
            raise ValueError(f'{rel}: 모르는 {sec} 종류 {kind}')
        new = wrap(sec, kind, render(parts[(sec, kind, lang)], page_slots(block), rel))
        return s[:m.start()] + new + s[m.end():]
    f = FIND_RE[sec].search(s)
    if not f:
        return s
    block = f.group(0)
    # 처음: 겉보기(표시자를 뺀 모양, 또는 태그·속성·글자 정규형)가 지금 구역과 같아지는 조각을 찾는다.
    # 언어 링크는 다른 페이지에서 복사해 왔을 수 있으니 비교 때는 페이지 값으로, 결과에는 계산 값으로 넣는다
    a = re.search(r'<a class="lang" href="([^"]*)"', block)
    for kind in SECTIONS[sec]:
        part = parts[(sec, kind, lang)]
        vals = page_slots(block, default_of(part, 'pg:fine'))
        seen = render(part, vals, rel, a.group(1) if a else None)
        if strip_markers(seen) == strip_markers(block) or canon(seen) == canon(block):
            return s[:f.start()] + wrap(sec, kind, render(part, vals, rel)) + s[f.end():]
    raise ValueError(f'{rel}: {sec}가 어느 조각과도 같지 않습니다(partials/{sec}.*.{lang}.html 와 비교)')


def pages(root):
    for p in sorted(root.rglob('*.html')):
        rel = p.relative_to(root).as_posix()
        if rel.startswith(SKIP):
            continue
        yield p, rel


def run(root, check):
    parts = load_partials(root)
    changed, errors = [], []
    for p, rel in pages(root):
        raw = p.read_bytes().decode('utf-8')
        crlf = CR + NL in raw
        s = raw.replace(CR + NL, NL)
        t = s
        for sec in SECTIONS:
            try:
                t = rewrite_section(sec, rel, t, parts)
            except ValueError as e:
                errors.append(str(e))
                continue
            if check and block_re(sec).search(s) is None and FIND_RE[sec].search(s):
                errors.append(f'{rel}: {sec}에 <!--shell:{sec} 종류--> 표시자가 없습니다')
        if t != s:
            changed.append(rel)
            if not check:
                p.write_bytes((t.replace(NL, CR + NL) if crlf else t).encode('utf-8'))
    return changed, errors


def main():
    args = sys.argv[1:]
    check = '--check' in args
    root = Path(args[args.index('--root') + 1]).resolve() if '--root' in args else Path(__file__).resolve().parent.parent
    changed, errors = run(root, check)
    for e in errors:
        print('오류:', e)
    if check:
        if changed or errors:
            if changed:
                print('머리·꼬리 조각(partials/)과 어긋난 페이지:', ', '.join(changed))
            print('로컬에서 python tools/build_shell.py 를 돌려 바뀐 파일을 같이 커밋하세요.')
            sys.exit(1)
        print('shell 검사 통과')
    else:
        print(f'shell 갱신 {len(changed)}개:', ', '.join(changed) if changed else '(변경 없음)')
        if errors:
            sys.exit(1)


if __name__ == '__main__':
    main()
