#!/usr/bin/env python3
"""에이전트 요약판(사진·역할·이름·한 줄·숫자 한 줄 + 팀 소개 링크)을 정본 agents.json에서 모든 페이지에 채운다(2026-10-18 지투).

왜: 같은 에이전트 소개가 제품 하단과 테크리포트 저자 칸에 손으로 복사돼 있어, 역할 이름 하나가 바뀌면 여러 곳을 고쳐야 했고
    실제로 페이지끼리 어긋난 적이 있다. 정본 하나를 고치면 그 에이전트가 나오는 모든 페이지가 같이 바뀌게 한다.

정본: agents.json(에이전트별 이름·역할·사진·한 줄·숫자 한 줄, 공용 문구 labels)
      partials/agents.mini.<언어>.html(요약판 모양 한 종. <!--ag:item-->은 에이전트마다 반복, <!--ag:stats-->는 숫자 줄)
      reports.json의 author_id·reviewers(테크리포트 글의 저자·검수 에이전트와 검수 표지)
페이지 표시자(ul.ag-mini부터 p.ag-more까지를 감싼다. 제목 h2와 section은 페이지 몫):
  <!--shell:agents ids=jitu,note-->...<!--/shell:agents-->  제품 하단 '맡은 에이전트': 숫자 줄 있음, 전체 보기 문구 labels.more
  <!--shell:agents report-->...<!--/shell:agents-->         테크리포트 저자 칸: 주소의 글을 reports.json에서 찾아 저자·검수자 순서,
                                                           역할 앞에 '저자 · '·'검수 표지 · ', 숫자 줄 없음(사진·전체 보기 문구는 제품 하단과 같다)
다른 도구와 겹치지 않는다: build_shell.py(머리·꼬리), build_menu.py(메뉴), build_reports.py(목록·이전/다음·꼬리 리포트 칸)는 이 구역을 건드리지 않는다.

사용: python tools/build_agents.py          다시 만들어 파일에 쓴다(표시자가 없는 ag-mini는 처음 한 번 지금 모양과 같은지 보고 표시자를 심는다)
      python tools/build_agents.py --check  표시자 구역이 정본과 다르거나, 표시자 없는 ag-mini가 있거나, reports.json 저자 이름이 어긋나면 종료코드 1
      --root <폴더>                          시험용으로 다른 폴더를 대상으로 돈다
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_shell import canon, lang_of, pages  # noqa: E402

NL = chr(10)
CR = chr(13)
BLOCK_RE = re.compile(r'<!--shell:agents ([^>]*?)-->(.*?)<!--/shell:agents-->', re.S)
FIND_RE = re.compile(r'<ul class="ag-mini">.*?</ul>\s*<p class="ag-more">.*?</p>', re.S)
ITEM_RE = re.compile(r'<!--ag:item-->(.*?)<!--/ag:item-->', re.S)
STATS_RE = re.compile(r'<!--ag:stats-->(.*?)<!--/ag:stats-->', re.S)
REPORT_RE = re.compile(r'^(?:ko/)?tech-report/([a-z0-9-]+)/index\.html$')


def load(root):
    data = json.loads((root / 'agents.json').read_text(encoding='utf-8'))
    agents = {a['id']: a for a in data['agents']}
    reports = json.loads((root / 'reports.json').read_text(encoding='utf-8'))['reports']
    parts = {lang: (root / 'partials' / f'agents.mini.{lang}.html').read_text(encoding='utf-8').replace(CR + NL, NL).strip(NL)
             for lang in ('en', 'ko')}
    return data['labels'], agents, {r['slug']: r for r in reports}, parts


def lint(agents, reports):
    errs = []
    for slug, r in reports.items():
        ids = [r.get('author_id')] + [v['id'] for v in r.get('reviewers', [])]
        for i in ids:
            if i not in agents:
                errs.append(f'reports.json {slug}: agents.json에 없는 에이전트 {i}')
        a = agents.get(r.get('author_id'))
        if a:
            for lang in ('en', 'ko'):
                if r['author'][lang] != a['name'][lang]:
                    errs.append(f'reports.json {slug}: author {r["author"][lang]} 가 agents.json {a["id"]} 이름 {a["name"][lang]} 과 다릅니다')
    return errs


def people(spec, rel, labels, reports, lang):
    """표시자 내용 -> [(에이전트 id, 역할 앞 표지 또는 None)], 모드."""
    if spec.strip() == 'report':
        m = REPORT_RE.match(rel)
        if not m or m.group(1) not in reports:
            raise ValueError(f'{rel}: report 표시자인데 reports.json에서 글을 찾지 못했습니다')
        r = reports[m.group(1)]
        out = [(r['author_id'], labels['author'][lang])]
        out += [(v['id'], v['as'][lang]) for v in r.get('reviewers', [])]
        return out, 'report'
    m = re.fullmatch(r'ids=([a-z0-9,]+)', spec.strip())
    if not m:
        raise ValueError(f'{rel}: 모르는 표시자 shell:agents {spec}')
    return [(i, None) for i in m.group(1).split(',')], 'product'


def render(spec, rel, labels, agents, reports, parts):
    lang = lang_of(rel)
    who, mode = people(spec, rel, labels, reports, lang)
    part = parts[lang]
    item_t = ITEM_RE.search(part).group(1)
    items = []
    for i, label in who:
        if i not in agents:
            raise ValueError(f'{rel}: agents.json에 없는 에이전트 {i}')
        a = agents[i]
        stats = a['stats'][lang] if mode == 'product' else ''
        t = STATS_RE.sub(lambda m: m.group(1) if stats else '', item_t)
        t = (t.replace('%PHOTO%', a['photo'])
              .replace('%AS%', f'{label} · ' if label else '')
              .replace('%NAME%', a['name'][lang]).replace('%ROLE%', a['role'][lang])
              .replace('%LINE%', a['line'][lang]).replace('%STATS%', stats))
        items.append(t)
    more = labels['more'][lang]
    return ITEM_RE.sub(lambda m: ''.join(items), part).replace('%MORE%', more)


def guess_spec(rel, block, agents):
    if REPORT_RE.match(rel):
        return 'report'
    lang = lang_of(rel)
    by_name = {a['name'][lang]: a['id'] for a in agents.values()}
    names = re.findall(r'<h3>(.*?)</h3>', block)
    if not names or any(n not in by_name for n in names):
        raise ValueError(f'{rel}: ag-mini 이름 {names} 을 agents.json에서 찾지 못했습니다')
    return 'ids=' + ','.join(by_name[n] for n in names)


def run(root, check):
    labels, agents, reports, parts = load(root)
    errors = lint(agents, reports)
    changed, used = [], {}
    for p, rel in pages(root):
        raw = p.read_bytes().decode('utf-8')
        crlf = CR + NL in raw
        s = raw.replace(CR + NL, NL)
        t = s
        try:
            def fill(m):
                return f'<!--shell:agents {m.group(1)}-->' + render(m.group(1), rel, labels, agents, reports, parts) + '<!--/shell:agents-->'
            t = BLOCK_RE.sub(fill, t)
            # 표시자 밖에 남은 ag-mini(처음 한 번): 지금 모양과 같게 그려지는 표시자를 찾아 심는다
            marked = [m.span() for m in BLOCK_RE.finditer(t)]
            loose = [f for f in FIND_RE.finditer(t) if not any(a <= f.start() < b for a, b in marked)]
            for f in reversed(loose):
                block = f.group(0)
                spec = guess_spec(rel, block, agents)
                new = render(spec, rel, labels, agents, reports, parts)
                if new != block and canon(new) != canon(block):
                    raise ValueError(f'{rel}: ag-mini가 agents.json으로 그린 모양과 다릅니다(먼저 agents.json을 맞추세요)')
                if check:
                    errors.append(f'{rel}: ag-mini에 <!--shell:agents ...--> 표시자가 없습니다')
                t = t[:f.start()] + f'<!--shell:agents {spec}-->' + new + '<!--/shell:agents-->' + t[f.end():]
        except ValueError as e:
            errors.append(str(e))
            continue
        for m in BLOCK_RE.finditer(t):
            used.setdefault(rel, []).append(m.group(1))
        if t != s:
            changed.append(rel)
            if not check:
                p.write_bytes((t.replace(NL, CR + NL) if crlf else t).encode('utf-8'))
    return changed, errors, used


def main():
    args = sys.argv[1:]
    check = '--check' in args
    root = Path(args[args.index('--root') + 1]).resolve() if '--root' in args else Path(__file__).resolve().parent.parent
    changed, errors, used = run(root, check)
    for e in errors:
        print('오류:', e)
    if check:
        if changed or errors:
            if changed:
                print('에이전트 요약판이 정본(agents.json, reports.json, partials/agents.mini.*)과 어긋난 페이지:', ', '.join(changed))
            print('로컬에서 python tools/build_agents.py 를 돌려 바뀐 파일을 같이 커밋하세요.')
            sys.exit(1)
        print(f'agents 검사 통과({len(used)}쪽)')
    else:
        print(f'agents 갱신 {len(changed)}개:', ', '.join(changed) if changed else '(변경 없음)')
        if errors:
            sys.exit(1)


if __name__ == '__main__':
    main()
