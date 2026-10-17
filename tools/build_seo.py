#!/usr/bin/env python3
"""구조화 데이터(JSON-LD) 생성기(2026-10-17 지투-SEO).

정본: 각 페이지의 <title>, meta description, canonical, html lang, 화면에 보이는 FAQ(<details><summary>),
      그리고 reports.json(테크리포트 날짜). 페이지 문구를 고치면 이 스크립트를 다시 돌리면 된다.

사용:
  python tools/build_seo.py          모든 공개 페이지 <head>에 <!--seo:ld-->...<!--/seo:ld--> 블록을 채운다
  python tools/build_seo.py --check  블록이 정본과 다르면 실패(종료 코드 1)

넣는 것:
  - 모든 페이지: Organization(Carvit), WebPage
  - 홈(/, /ko/): WebSite
  - 홈이 아닌 페이지: BreadcrumbList
  - 제품 페이지(ux-mcp, pass, create): SoftwareApplication
  - 테크리포트 글: TechArticle
  - 화면에 FAQ가 보이는 페이지만: FAQPage(질문·답은 화면 문구 그대로)
"""
import html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://carvit.ai'
ORG_ID = SITE + '/#org'
SKIP = {'google52b4e332bf87f14f.html'}

ORG = {
    '@type': 'Organization', '@id': ORG_ID, 'name': 'Carvit', 'alternateName': 'Carvit AI', 'url': SITE + '/',
    'logo': {'@type': 'ImageObject', 'url': SITE + '/assets/logo/apple-touch-icon.png', 'width': 180, 'height': 180},
    'description': 'Carvit builds AI agent tools for startups, including Carvit UX MCP, which connects a company UX guide to AI coding agents.',
    'parentOrganization': {'@type': 'Organization', 'name': 'Simplifier', 'url': 'https://simplifier.co.kr/'},
    'founder': {'@type': 'Person', 'name': 'Simon', 'sameAs': ['https://www.linkedin.com/in/simplifier/']},
}
PRODUCTS = {
    'ux-mcp': dict(name='Carvit UX MCP', cat='DeveloperApplication',
                   en='MCP server that turns a company UX guide into an agent guide so AI coding agents build screens that follow it.',
                   ko='회사 UX 가이드를 에이전트용 가이드로 만들어 AI 코딩 에이전트가 그 가이드대로 화면을 만들게 하는 MCP 서버.'),
    'pass': dict(name='Carvit Pass', cat='SecurityApplication',
                 en='Key vault for AI agents: agents request keys by name and the vault injects the value without showing it.',
                 ko='AI 에이전트용 키 금고. 에이전트는 이름으로만 요청하고 금고가 값을 보여 주지 않고 넣어 줍니다.'),
    'create': dict(name='Carvit Create', cat='MultimediaApplication',
                   en='AI agents run the video pipeline, from performance analysis and topic ideas to production and publishing.',
                   ko='성과 분석, 주제 제안, 영상 제작, 채널 운영까지 AI 에이전트가 이어서 하는 영상 제작 도구.'),
}
CRUMB = {'en': {'tech-report': 'Tech Report', 'ux-mcp': 'Carvit UX MCP', 'pass': 'Carvit Pass', 'create': 'Carvit Create',
                'brand': 'Brand', 'team': 'Team', 'privacy': 'Privacy Policy', 'terms': 'Terms of Service', 'guide': 'Guide'},
         'ko': {'tech-report': '테크리포트', 'ux-mcp': 'Carvit UX MCP', 'pass': 'Carvit Pass', 'create': 'Carvit Create',
                'brand': '브랜드', 'team': '팀', 'privacy': '개인정보처리방침', 'terms': '서비스 이용약관', 'guide': '가이드'}}


def text(s):
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'</p>\s*<p[^>]*>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def meta(s, attr, key):
    m = re.search(rf'<meta {attr}="{re.escape(key)}" content="([^"]*)"', s)
    return html.unescape(m.group(1)) if m else None


def build(path, s, reports):
    rel = path.relative_to(ROOT).as_posix()
    lang = re.search(r'<html lang="([a-z]+)"', s).group(1)
    canon = re.search(r'<link rel="canonical" href="([^"]+)"', s)
    if not canon or re.search(r'<meta name="robots" content="[^"]*noindex', s):
        return None
    url = canon.group(1)
    title = text(re.search(r'<title>(.*?)</title>', s, re.S).group(1))
    desc = meta(s, 'name', 'description')
    image = meta(s, 'property', 'og:image')
    inlang = 'ko-KR' if lang == 'ko' else 'en'
    segs = [x for x in url[len(SITE):].strip('/').split('/') if x]
    if segs and segs[0] == 'ko':
        segs = segs[1:]
    home = SITE + ('/ko/' if lang == 'ko' else '/')
    graph = [ORG]
    page = {'@type': 'WebPage', '@id': url + '#page', 'url': url, 'name': title, 'inLanguage': inlang,
            'isPartOf': {'@id': SITE + '/#website'}, 'publisher': {'@id': ORG_ID}}
    if desc:
        page['description'] = desc
    if image:
        page['primaryImageOfPage'] = {'@type': 'ImageObject', 'url': image}
    graph.append(page)
    if not segs:
        graph.append({'@type': 'WebSite', '@id': SITE + '/#website', 'url': SITE + '/', 'name': 'Carvit',
                      'alternateName': 'Carvit AI', 'inLanguage': ['en', 'ko-KR'], 'publisher': {'@id': ORG_ID}})
    else:
        items = [{'@type': 'ListItem', 'position': 1, 'name': 'Carvit', 'item': home}]
        acc = home
        for i, sg in enumerate(segs):
            acc = acc + sg + '/'
            name = CRUMB[lang].get(sg)
            if i == len(segs) - 1 or name is None:
                h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
                og = meta(s, 'property', 'og:title')
                name = name if (name and i < len(segs) - 1) else (og or (text(h1.group(1)) if h1 else title))
                if sg in CRUMB[lang] and i == len(segs) - 1:
                    name = CRUMB[lang][sg]
            items.append({'@type': 'ListItem', 'position': i + 2, 'name': name, 'item': acc})
        graph.append({'@type': 'BreadcrumbList', '@id': url + '#breadcrumb', 'itemListElement': items})
        page['breadcrumb'] = {'@id': url + '#breadcrumb'}
    if len(segs) == 1 and segs[0] in PRODUCTS:
        pr = PRODUCTS[segs[0]]
        graph.append({'@type': 'SoftwareApplication', '@id': SITE + '/' + segs[0] + '/#app', 'name': pr['name'],
                      'applicationCategory': pr['cat'], 'operatingSystem': 'Any', 'url': url, 'inLanguage': inlang,
                      'description': pr[lang], 'publisher': {'@id': ORG_ID}, 'brand': {'@id': ORG_ID}})
        page['about'] = {'@id': SITE + '/' + segs[0] + '/#app'}
    if len(segs) == 2 and segs[0] == 'tech-report' and segs[1] in reports:
        r = reports[segs[1]]
        art = {'@type': 'TechArticle', '@id': url + '#article', 'headline': meta(s, 'property', 'og:title') or title,
               'description': desc, 'inLanguage': inlang, 'url': url, 'mainEntityOfPage': {'@id': url + '#page'},
               'datePublished': r['date'], 'author': {'@id': ORG_ID}, 'publisher': {'@id': ORG_ID}}
        if image:
            art['image'] = image
        graph.append(art)
    qa = re.findall(r'<details[^>]*>\s*<summary[^>]*>(.*?)</summary>\s*<div class="ans">(.*?)</div>\s*</details>', s, re.S)
    if qa:
        graph.append({'@type': 'FAQPage', '@id': url + '#faq', 'inLanguage': inlang, 'mainEntity': [
            {'@type': 'Question', 'name': text(q), 'acceptedAnswer': {'@type': 'Answer', 'text': text(a)}} for q, a in qa]})
    body = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':'))
    body = body.replace('</', '<\\/')
    return '<!--seo:ld--><script type="application/ld+json">' + body + '</script><!--/seo:ld-->'


def main():
    check = '--check' in sys.argv
    reports = {r['slug']: r for r in json.loads((ROOT / 'reports.json').read_text(encoding='utf-8'))['reports']}
    bad = 0
    for p in sorted(ROOT.rglob('index.html')):
        if any(part.startswith('.') or part in ('tools', 'assets') for part in p.relative_to(ROOT).parts):
            continue
        s = p.read_text(encoding='utf-8')
        blk = build(p, s, reports)
        if blk is None:
            continue
        if '<!--seo:ld-->' in s:
            new = re.sub(r'<!--seo:ld-->.*?<!--/seo:ld-->', lambda m: blk, s, count=1, flags=re.S)
        else:
            new = s.replace('</head>', blk + '</head>', 1)
        if new != s:
            bad += 1
            print(('다름 ' if check else '씀 ') + p.relative_to(ROOT).as_posix())
            if not check:
                p.write_text(new, encoding='utf-8')
    if check and bad:
        sys.exit(1)


if __name__ == '__main__':
    main()
