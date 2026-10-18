#!/usr/bin/env python3
"""build_agents.py 시험: 사본 폴더에서 agents.json의 역할 이름 하나를 바꾸면 ① 검사가 실패하고 ② 다시 돌리면 그 에이전트가 나오는
모든 페이지(제품 하단·테크리포트 저자 칸)가 같이 바뀌며 ③ 다른 칸·다른 언어·다른 에이전트는 그대로인지 본다.
reports.json 저자 이름이 agents.json과 어긋나거나 표시자 없는 요약판이 생기면 검사가 잡는지도 본다. 사용: python tools/test_build_agents.py"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / 'tools' / 'build_agents.py'
MARK = re.compile(r'<!--shell:agents ([^>]*?)-->')


def sh(root, *a):
    r = subprocess.run([sys.executable, str(TOOL), '--root', str(root), *a], capture_output=True, text=True, encoding='utf-8')
    return r.returncode, r.stdout + r.stderr


def read(p):
    return p.read_bytes().decode('utf-8')


def pages_with(tmp, agent_id, lang):
    """표시자와 reports.json으로 그 에이전트가 나오는 페이지를 센다(고정 숫자 대신)."""
    reports = {r['slug']: r for r in json.loads(read(tmp / 'reports.json'))['reports']}
    out = []
    for p in tmp.rglob('*.html'):
        rel = p.relative_to(tmp).as_posix()
        if rel.startswith('partials/') or (rel.startswith('ko/') != (lang == 'ko')):
            continue
        for spec in MARK.findall(read(p)):
            if spec == 'report':
                r = reports[rel.split('tech-report/')[1].split('/')[0]]
                ids = [r['author_id']] + [v['id'] for v in r['reviewers']]
            else:
                ids = spec.split('=', 1)[1].split(',')
            if agent_id in ids:
                out.append(rel)
                break
    return sorted(out)


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        for p in ROOT.rglob('*'):
            rel = p.relative_to(ROOT)
            if rel.parts[0] in ('.git', 'assets') or not p.is_file() or p.suffix not in ('.html', '.json'):
                continue
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, tmp / rel)
        code, out = sh(tmp, '--check')
        assert code == 0, '처음 상태 검사가 실패: ' + out
        before = {p.relative_to(tmp).as_posix(): read(p) for p in tmp.rglob('*.html')}

        # 역할 이름 하나 바꾸기: 지투 영어 역할
        aj = tmp / 'agents.json'
        data = json.loads(read(aj))
        jitu = next(a for a in data['agents'] if a['id'] == 'jitu')
        old, new = jitu['role']['en'], 'Product Lead Agent'
        assert all(new not in s for s in before.values())
        jitu['role']['en'] = new
        aj.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        expect = pages_with(tmp, 'jitu', 'en')
        assert any(r.startswith('tech-report/') for r in expect) and any(not r.startswith('tech-report/') for r in expect), expect

        code, out = sh(tmp, '--check')
        assert code == 1 and all(r in out for r in expect), '역할을 바꿨는데 검사가 통과함: ' + out
        code, out = sh(tmp)
        assert code == 0, out
        after = {p.relative_to(tmp).as_posix(): read(p) for p in tmp.rglob('*.html')}
        changed = sorted(r for r in after if after[r] != before[r])
        assert changed == expect, f'바뀐 페이지 {changed} != 지투가 나오는 영어 페이지 {expect}'
        for r in changed:
            # 그 페이지에서 바뀐 것은 역할 이름뿐(사진·이름·한 줄·숫자·링크·다른 에이전트 칸 그대로)
            assert after[r].count(new) >= 2, r  # 역할 줄과 사진 alt
            assert after[r].replace(new, old) == before[r], f'{r}: 역할 말고 다른 것도 바뀜'
        assert sh(tmp, '--check')[0] == 0

        # reports.json 저자 이름이 agents.json과 어긋나면 검사 실패
        rj = tmp / 'reports.json'
        rs = read(rj)
        rj.write_text(rs.replace('"en": "Tam"', '"en": "Tom"', 1), encoding='utf-8')
        code, out = sh(tmp, '--check')
        assert code == 1 and 'author' in out, '저자 이름 어긋남을 놓침: ' + out
        rj.write_text(rs, encoding='utf-8')

        # 표시자 없는 요약판(다른 페이지에서 복사해 온 새 페이지): 검사가 잡고, 돌리면 표시자를 심는다
        new_page = tmp / 'new-page' / 'index.html'
        new_page.parent.mkdir()
        new_page.write_text(re.sub(r'<!--/?shell:agents[^>]*-->', '', after['pass/index.html']), encoding='utf-8')
        assert sh(tmp, '--check')[0] == 1, '표시자 없는 요약판을 검사가 놓침'
        sh(tmp)
        assert '<!--shell:agents ids=tam-->' in read(new_page)
        print('test_build_agents 통과(역할 1개 변경 -> 영어', len(expect), '쪽 동시 갱신, 다른 칸 그대로)')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
