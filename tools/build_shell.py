#!/usr/bin/env python3
"""꼬리(footer)를 조각 파일 한 곳에서 모든 페이지에 채운다(2026-10-18 지투, build_menu.py와 같은 방식).

정본: partials/foot.<종류>.<언어>.html   종류 = home(홈) | full(제품·팀 열 있는 하위) | short(정책·리포트 하위), 언어 = en | ko
페이지: <!--shell:foot 종류-->  <footer ...>...</footer>  <!--/shell:foot-->  (언어는 경로로 정한다: ko/ 아래면 ko)

조각 안의 칸(slot): 다른 도구나 페이지가 주인인 구역. 조각을 다시 써도 페이지 값을 그대로 둔다.
  <!--mn:foot--><!--/mn:foot-->   Carvit MCP 열 링크. 주인 build_menu.py(menu.json subnav)
  <!--rp:foot--><!--/rp:foot-->   테크리포트 목록. 주인 build_reports.py(reports.json)
  <!--pg:fine-->기본값<!--/pg:fine-->  맨 아래 한 줄. 페이지에 이 표시자가 있으면 페이지 값(테크리포트 글의 번호·버전·날짜),
                                     없으면 조각의 기본값을 표시자 없이 넣는다.

사용: python tools/build_shell.py          다시 만들어 파일에 쓴다(새 페이지는 꼬리를 아무 페이지에서 복사해 두면 된다)
      python tools/build_shell.py --check  페이지 꼬리가 조각과 같은지만 검사(다르면 종료코드 1, 깃허브 menu-check가 쓴다)
      --root <폴더>                         시험용으로 다른 폴더를 대상으로 돈다
꼬리를 고친 뒤에는: python tools/build_shell.py && python tools/build_menu.py && python tools/build_reports.py
"""
import re, sys
from pathlib import Path

NL = chr(10)
CR = chr(13)
KINDS = ('home', 'full', 'short')
KEEP = ('mn:foot', 'rp:foot')       # 늘 표시자를 남기고 페이지 값을 쓴다
OVERRIDE = ('pg:fine',)             # 페이지에 표시자가 있을 때만 페이지 값
SLOT_RE = re.compile(r'<!--((?:mn|rp|pg):[a-z]+)-->(.*?)<!--/\1-->', re.S)
BLOCK_RE = re.compile(r'<!--shell:foot ([a-z]+)-->(.*?)<!--/shell:foot-->', re.S)
FOOTER_RE = re.compile(r'<footer class="(?:foot|bottom)">.*?</footer>', re.S)
MCP_COL_RE = re.compile(r'(<div><h5><a href="(?:/ko)?/ux-mcp/">(?:UX MCP|<span class="nowrap">Carvit MCP</span>)</a></h5>)(.*?)(</div>)', re.S)
FINE_RE = re.compile(r'(<p class="fine">)(.*?)(</p>)', re.S)
SKIP = ('assets/', '.git', 'node_modules', '_preview/', 'partials/', 'google')


def lang_of(rel):
    return 'ko' if rel.startswith('ko/') else 'en'


def read_text(p):
    return p.read_bytes().decode('utf-8').replace(CR + NL, NL)


def load_partials(root):
    parts = {}
    for k in KINDS:
        for lang in ('en', 'ko'):
            p = root / 'partials' / f'foot.{k}.{lang}.html'
            parts[(k, lang)] = read_text(p).strip(NL)
    return parts


def strip_markers(s):
    return SLOT_RE.sub(lambda m: m.group(2), s)


def page_slots(block, default_fine=None):
    """페이지 꼬리에서 칸 값을 읽는다. 표시자가 없으면(처음 한 번) 구조로 찾는다."""
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


def render(partial, vals):
    def fill(m):
        name, default = m.group(1), m.group(2)
        if name in KEEP:
            return f'<!--{name}-->' + vals.get(name, '') + f'<!--/{name}-->'
        if name in vals:
            return f'<!--{name}-->' + vals[name] + f'<!--/{name}-->'
        return default
    return SLOT_RE.sub(fill, partial)


def wrap(kind, body):
    return f'<!--shell:foot {kind}-->' + body + '<!--/shell:foot-->'


def rewrite(rel, s, parts):
    """새 내용을 돌려준다. 맞는 조각을 못 찾으면 ValueError."""
    lang = lang_of(rel)
    m = BLOCK_RE.search(s)
    if m:
        kind, block = m.group(1), m.group(2)
        if (kind, lang) not in parts:
            raise ValueError(f'{rel}: 모르는 꼬리 종류 {kind}')
        part = parts[(kind, lang)]
        new = wrap(kind, render(part, page_slots(block)))
        return s[:m.start()] + new + s[m.end():]
    f = FOOTER_RE.search(s)
    if not f:
        return s
    block = f.group(0)
    # 처음: 겉보기(표시자를 뺀 모양)가 지금 꼬리와 똑같아지는 조각을 찾는다
    for kind in KINDS:
        part = parts[(kind, lang)]
        out = render(part, page_slots(block, default_of(part, 'pg:fine')))
        if strip_markers(out) == strip_markers(block):
            return s[:f.start()] + wrap(kind, out) + s[f.end():]
    raise ValueError(f'{rel}: 꼬리가 어느 조각과도 같지 않습니다(partials/foot.*.{lang}.html 와 비교)')


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
        try:
            t = rewrite(rel, s, parts)
        except ValueError as e:
            errors.append(str(e))
            continue
        if check and BLOCK_RE.search(s) is None and FOOTER_RE.search(s):
            errors.append(f'{rel}: 꼬리에 <!--shell:foot 종류--> 표시자가 없습니다')
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
                print('꼬리 조각(partials/)과 어긋난 페이지:', ', '.join(changed))
            print('로컬에서 python tools/build_shell.py 를 돌려 바뀐 파일을 같이 커밋하세요.')
            sys.exit(1)
        print('shell 검사 통과')
    else:
        print(f'shell 갱신 {len(changed)}개:', ', '.join(changed) if changed else '(변경 없음)')
        if errors:
            sys.exit(1)


if __name__ == '__main__':
    main()
