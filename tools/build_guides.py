#!/usr/bin/env python3
"""러닝 가이드 글을 글별 정적 HTML(guide/<id>.html)로 미리 렌더한다.

원본: data/blog/index.json + data/blog/<id>.json (본문 HTML은 JSON의 html 필드)
선택: data/blog/redirects.json  {"옛id": "대상id", ...}  — 병합된 글의 옛 주소. guide/<옛id>.html 이동 페이지를 만든다.
결과:
  guide/<id>.html          본문 전체가 HTML에 들어 있는 정적 글 페이지(JS 없이 읽힘), 고유 title·description·canonical·Article JSON-LD
  post.html                /*GUIDEMAP*/ 블록 갱신 — 옛 주소 post.html?id=<id> 를 정적 페이지로 보낸다
  blog.html                <!--GUIDELIST--> 블록 갱신 — 목록을 HTML에 미리 넣는다(JS가 다시 그려도 같은 링크)
daily_publish.sh 가 매일 돌린다. 새 글을 data/blog 에 넣은 뒤 직접 돌려도 된다: python3 tools/build_guides.py
"""
import json, os, re, glob, html as H

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = os.environ.get('SITE_URL', 'https://runwoori.com').rstrip('/')
BLOG = os.path.join(ROOT, 'data', 'blog')
OUT = os.path.join(ROOT, 'guide')
SEP = '<span class="ed-sep">·</span>'


def esc(s): return H.escape(str(s or ''), quote=True)
def js(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
def p2(n): return f'{int(n):02d}'


def snippets():
    """post.html 의 AdSense·GA4 블록을 그대로 가져온다(광고 밀도는 기존 글 페이지와 같다)."""
    s = open(os.path.join(ROOT, 'post.html'), encoding='utf8').read()
    out = []
    for tag in ('ADSENSE', 'GA4'):
        m = re.search(rf'<!--{tag}:START-->.*?<!--{tag}:END-->', s, re.S)
        if m: out.append(m.group(0))
    return '\n'.join(out)


def url_of(pid): return f'{SITE}/guide/{pid}.html'


def fix_links(body, pid, target):
    """본문 안의 옛 글 주소와 #앵커를 정적 주소로 바꾼다(<base href="/"> 기준)."""
    body = re.sub(r'href="post\.html\?id=([a-z0-9-]+)(#[^"]*)?"', lambda m: f'href="guide/{target(m.group(1))}.html{m.group(2) or ""}"', body)
    body = re.sub(r'href="#([^"]+)"', lambda m: f'href="guide/{pid}.html#{m.group(1)}"', body)
    return body


def row(p, i=None):  # app.js blogRow() 와 같은 마크업
    return (f'<a class="ed-guide ed-post-row" href="guide/{esc(p["id"])}.html"><span class="ix">{p2(i if i is not None else p["no"])}</span>'
            f'<div><span class="ed-label">{esc(p["level"])}{SEP}{p["minutes"]}분</span><h3>{esc(p["title"])}</h3><p>{esc(p["summary"])}</p></div>'
            f'<span class="ed-arrow" style="color:var(--ink-3)" aria-hidden="true">→</span></a>')


HEAD = '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<base href="/">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#F6F2EA">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{url}"><meta property="og:url" content="{url}">
{snip}
<meta property="og:site_name" content="Run우리"><meta property="og:type" content="article"><meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:image" content="{site}/assets/icons/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Run우리 — 마라톤·러닝 대회 일정">
<meta property="article:published_time" content="{pub}"><meta property="article:modified_time" content="{mod}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}"><meta name="twitter:image" content="{site}/assets/icons/og-image.png">
<link rel="icon" href="favicon.ico" sizes="48x48"><link rel="icon" href="assets/logo/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="assets/logo/apple-touch-icon.png"><link rel="manifest" href="manifest.webmanifest">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" media="print" onload="this.media='all'">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap"></noscript>
<link rel="stylesheet" href="design-tokens.css"><link rel="stylesheet" href="components.css"><link rel="stylesheet" href="site.css">
<script type="application/ld+json">{ld}</script>
<script type="application/ld+json">{crumbs}</script>
<script src="app.js"></script></head><body>
'''

NOTE = ('이 글은 일반적인 참고 정보이며 개인의 건강 상태에 맞춘 처방이 아니에요. 훈련 계획과 페이스, 심박 수치는 사람마다 크게 다를 수 있어요. '
        '가슴 통증, 어지러움, 지속되는 통증이나 지병이 있다면 시작하기 전에 의사와 상담하세요.')


def page(P, prev, nxt, same, snip, target):
    pid, url = P['id'], url_of(P['id'])
    pub = P.get('date') or ''
    mod = P.get('dateModified') or P.get('date_modified') or pub
    title = f"{P['title']} | Run우리 러닝 가이드"
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': P['title'], 'description': P['summary'], 'inLanguage': 'ko',
          'articleSection': P['level'], 'datePublished': pub, 'dateModified': mod, 'url': url,
          'mainEntityOfPage': {'@type': 'WebPage', '@id': url}, 'image': f'{SITE}/assets/icons/og-image.png',
          'author': {'@type': 'Organization', 'name': 'Run우리', 'url': SITE + '/'},
          'publisher': {'@type': 'Organization', 'name': 'Run우리', 'url': SITE + '/', 'logo': {'@type': 'ImageObject', 'url': f'{SITE}/assets/logo/apple-touch-icon.png'}}}
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Run우리', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': '러닝 가이드', 'item': SITE + '/blog.html'},
        {'@type': 'ListItem', 'position': 3, 'name': P['title'], 'item': url}]}
    lv = esc(P['level']); lvq = esc(P['level'])
    date_html = f'{SEP}<time datetime="{esc(pub)}">{esc(pub.replace("-", "."))} 게시</time>' if pub else ''
    if mod and mod != pub: date_html += f'{SEP}<time datetime="{esc(mod)}">{esc(mod.replace("-", "."))} 수정</time>'
    nav_a = lambda p, rel, lab: (f'<a href="guide/{esc(p["id"])}.html" rel="{rel}"><span class="ed-label">{lab}</span><b>{esc(p["title"])}</b></a>' if p else '<span></span>')
    more = (f'<section class="ed-section ed-post-more"><div class="ed-section-head"><h2 class="ed-h2">{lv} 글 더 보기</h2><a class="ed-link" href="blog.html?level={lvq}">전체 보기 →</a></div>'
            f'<div class="ed-list" style="border-top:0">{"".join(row(p) for p in same)}</div></section>') if same else ''
    body = f'''
<main class="ed-wrap" id="main"><div id="view">
    <article class="ed-post">
      <div class="ed-post-top"><a class="ed-link ed-small" href="blog.html?level={lvq}">← 러닝 가이드 · {lv}</a></div>
      <header class="ed-post-head">
        <div class="ed-label accent">{lv}{SEP}읽는 시간 {P['minutes']}분{date_html}</div>
        <h1 class="ed-h1 ed-post-title">{esc(P['title'])}</h1>
        <p class="ed-lede">{esc(P['summary'])}</p>
      </header>
      <div class="ed-prose">{fix_links(P['html'], pid, target)}</div>
      <p class="ed-note ed-post-note">{NOTE}</p>
      <nav class="ed-post-nav" aria-label="이전·다음 글">
        {nav_a(prev, 'prev', '이전 글')}
        {nav_a(nxt, 'next', '다음 글')}
      </nav>
    </article>
    {more}
</div></main>
<script>layout('blog');</script></body></html>
'''
    return HEAD.format(title=esc(title), desc=esc(P['summary']), url=url, snip=snip, site=SITE, pub=esc(pub), mod=esc(mod),
                       ld=js(ld), crumbs=js(crumbs)) + body


def moved_page(old, P, snip):
    url = url_of(P['id'])
    return (HEAD.split('<script type="application/ld+json">')[0]
            .replace('<meta name="robots" content="index,follow">', f'<meta http-equiv="refresh" content="0; url=/guide/{esc(P["id"])}.html">')
            .format(title=esc(P['title'] + ' | Run우리 러닝 가이드'), desc=esc(P['summary']), url=url, snip='', site=SITE, pub='', mod='')
            + f'<script src="app.js"></script></head><body><main class="ed-wrap" id="main"><div style="padding:40px var(--page-x)"><div class="ed-label">러닝 가이드</div>'
            f'<h1 class="ed-h1" style="margin:12px 0 10px">글을 옮겼어요</h1><p class="ed-lede">이 내용은 <a class="ed-link" href="guide/{esc(P["id"])}.html">{esc(P["title"])}</a> 글로 합쳤어요.</p></div></main>'
            f'<script>layout(\'blog\');location.replace(\'/guide/{esc(P["id"])}.html\'+location.hash);</script></body></html>\n')


def replace_block(path, start, end, content):
    s = open(path, encoding='utf8').read()
    if start not in s or end not in s:
        raise SystemExit(f'{os.path.basename(path)} 에 {start} 표시가 없어요. 중단합니다.')
    s2 = re.sub(re.escape(start) + r'.*?' + re.escape(end), lambda m: start + content + end, s, flags=re.S)
    if s2 != s: open(path, 'w', encoding='utf8').write(s2)


def main():
    idx = json.load(open(os.path.join(BLOG, 'index.json'), encoding='utf8'))
    posts = idx['posts']
    rp = os.path.join(BLOG, 'redirects.json')
    redirects = json.load(open(rp, encoding='utf8')) if os.path.exists(rp) else {}
    ids = {p['id'] for p in posts}
    target = lambda i: redirects.get(i, i) if redirects.get(i) in ids else i
    snip = snippets()
    os.makedirs(OUT, exist_ok=True)
    written, full = set(), {}
    for i, meta in enumerate(posts):
        P = {**meta, **json.load(open(os.path.join(BLOG, meta['id'] + '.json'), encoding='utf8'))}
        full[P['id']] = P
        same = [p for p in posts if p['level'] == P['level'] and p['id'] != P['id']][:3]
        html = page(P, posts[i - 1] if i > 0 else None, posts[i + 1] if i + 1 < len(posts) else None, same, snip, target)
        if '불러오는 중' in html: raise SystemExit(f'{P["id"]}: 정적 페이지에 "불러오는 중"이 남았어요.')
        open(os.path.join(OUT, P['id'] + '.html'), 'w', encoding='utf8').write(html)
        written.add(P['id'] + '.html')
    for old, tgt in redirects.items():
        if old in ids or tgt not in full: continue
        open(os.path.join(OUT, old + '.html'), 'w', encoding='utf8').write(moved_page(old, full[tgt], snip))
        written.add(old + '.html')
    for f in glob.glob(os.path.join(OUT, '*.html')):
        if os.path.basename(f) not in written: os.remove(f)
    # post.html: 옛 주소 → 정적 페이지 지도
    gmap = {p['id']: f'guide/{p["id"]}.html' for p in posts}
    gmap.update({o: f'guide/{t}.html' for o, t in redirects.items() if t in ids and o not in ids})
    replace_block(os.path.join(ROOT, 'post.html'), '/*GUIDEMAP:START*/', '/*GUIDEMAP:END*/', 'var GUIDE_MAP=' + js(gmap) + ';')
    # blog.html: 목록을 HTML에 미리 넣는다
    replace_block(os.path.join(ROOT, 'blog.html'), '<!--GUIDELIST:START-->', '<!--GUIDELIST:END-->', ''.join(row(p) for p in posts))
    print(f'guide pages: {len([w for w in written if w[:-5] in ids])}편 + 이동 페이지 {len(written) - len([w for w in written if w[:-5] in ids])}개 → guide/<id>.html')


if __name__ == '__main__':
    main()
