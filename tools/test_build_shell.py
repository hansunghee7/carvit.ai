#!/usr/bin/env python3
"""build_shell.py 시험: 사본 폴더에서 조각을 고치면 ① 검사가 실패하고 ② 다시 돌리면 그 종류 페이지만 바뀌며
③ 다른 도구·페이지 칸(테크리포트 목록, MCP 열, 글별 맨 아래 줄)은 그대로인지 본다. 사용: python tools/test_build_shell.py"""
import re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / 'tools' / 'build_shell.py'


def sh(root, *a):
    r = subprocess.run([sys.executable, str(TOOL), '--root', str(root), *a], capture_output=True, text=True, encoding='utf-8')
    return r.returncode, r.stdout + r.stderr


def main():
    tmp = Path(tempfile.mkdtemp())
    try:
        for p in ROOT.rglob('*.html'):
            rel = p.relative_to(ROOT)
            if rel.parts[0] in ('.git', 'assets'):
                continue
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, tmp / rel)
        code, out = sh(tmp, '--check')
        assert code == 0, '처음 상태 검사가 실패: ' + out

        rp = 'tech-report/pass-security-model/index.html'
        before = (tmp / rp).read_text(encoding='utf-8')
        part = tmp / 'partials' / 'foot.short.en.html'
        part.write_text(part.read_text(encoding='utf-8').replace('>Brand</a></h5>', '>Brand X</a></h5>'), encoding='utf-8')
        code, out = sh(tmp, '--check')
        assert code == 1 and rp in out, '조각을 고쳤는데 검사가 통과함: ' + out

        code, out = sh(tmp)
        assert code == 0, out
        changed = [l for l in out.split(':', 1)[1].split(', ')]
        # 영어 short 꼬리를 쓰는 페이지 수는 글이 늘면 같이 는다(테크리포트 5 추가로 8→9). 고정 숫자 대신 표시자를 센다
        n_short_en = sum(1 for p in tmp.rglob('*.html') if '<!--shell:foot short-->' in p.read_text(encoding='utf-8')
                         and not p.relative_to(tmp).as_posix().startswith(('ko/', 'partials/')))
        assert len(changed) == n_short_en and all(not c.strip().startswith('ko/') for c in changed), f'영어 short {n_short_en}개만 바뀌어야 함: ' + out
        after = (tmp / rp).read_text(encoding='utf-8')
        assert 'Brand X' in after
        for keep in ('Tech Report 3 · Version 1.0', 'Tech Report 4</a>', 'https://mcp.carvit.ai/settings'):
            assert keep in before and keep in after, '칸 값이 사라짐: ' + keep
        assert sh(tmp, '--check')[0] == 0

        shutil.copy2(ROOT / 'partials' / 'foot.short.en.html', part)
        sh(tmp)
        # 표시자 없는 새 페이지: 기존 꼬리를 복사해 두면 처음 실행 때 맞는 조각을 찾아 표시자를 심는다
        new = tmp / 'new-page' / 'index.html'
        new.parent.mkdir()
        src = (ROOT / 'privacy' / 'index.html').read_text(encoding='utf-8')
        plain = re.sub(r'<!--/?(?:shell:foot(?: [a-z]+)?|mn:foot|pg:fine)-->', '', src)
        new.write_text(plain, encoding='utf-8')
        assert sh(tmp, '--check')[0] == 1, '표시자 없는 꼬리를 검사가 놓침'
        sh(tmp)
        assert '<!--shell:foot short-->' in new.read_text(encoding='utf-8')
        print('build_shell 시험 통과(4건)')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
