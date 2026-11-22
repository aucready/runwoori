#!/usr/bin/env python3
"""SEO P3 미리보기: 러닝화 허브·상세·용도·비교 정적 HTML. 공식 스펙만."""
from __future__ import annotations
import html, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import head_snippets as hs

SITE = os.environ.get('SITE_URL', 'https://runwoori.com').rstrip('/')
CHECKED_LABEL = '2026.11.22'

CAT_LABEL = {
    'daily': '데일리',
    'beginner': '입문',
    'value': '가성비',
    'stability': '안정화',
    'max_cushion': '맥스 쿠션',
    'tempo': '템포',
    'carbon': '카본·레이스',
    'trail': '트레일',
}
BEST = [
    ('beginner', '입문용 러닝화', '카본 플레이트가 공식 표기되지 않은 데일리·안정화 모델입니다. 우리가 착화감을 평가한 순위가 아니에요.'),
    ('value', '가성비 러닝화', '이번에 한국 공식 스토어 정가를 직접 확인한 모델 가운데, 정가가 19만 원 이하인 목록입니다.'),
    ('daily', '데일리 쿠션 러닝화', '공식 상품 페이지가 일상·데일리 러닝을 용도로 적거나, 우리가 데일리로 분류한 모델입니다.'),
    ('max_cushion', '맥스 쿠션 러닝화', '공식 페이지가 최대 쿠션으로 안내하거나, 고스택 데일리로 분류한 모델입니다. 착화감 평가는 적지 않았어요.'),
    ('tempo', '템포 러닝화', '공식 페이지가 스피드 훈련·템포 용도로 안내하는 모델입니다. 카본이 공식 표기되면 카본 목록에도 들어갑니다.'),
    ('stability', '안정화 러닝화', '공식 분류가 안정·지지(Stability/Structure)인 모델입니다. 평발이나 통증을 고친다는 뜻은 아니에요.'),
    ('half', '하프 마라톤 러닝화', '공식 페이지가 레이스 또는 템포·카본으로 안내하는 모델을 하프 거리 허브에 모아 두었어요. 이 신발을 신으면 기록이 단축된다는 뜻은 아닙니다.'),
    ('marathon', '풀코스·마라톤 러닝화', '공식 페이지가 로드 레이싱·마라톤용으로 안내하는 카본 모델입니다. 기록 단축을 약속하지 않아요.'),
    ('carbon', '카본 러닝화', '공식 페이지에 탄소 섬유 플레이트(또는 동등한 공식 표기)가 있는 모델입니다. 수명·단점은 공식이 적지 않은 항목은 비워 두었어요.'),
    ('trail', '트레일 러닝화', '이번에 공식 스펙을 확인한 트레일 모델이 있으면 여기에 모아요.'),
]


def esc(s):
    return html.escape('' if s is None else str(s), quote=True)


def load():
    global AFF
    data = json.loads((ROOT / 'data/shoes.json').read_text(encoding='utf8'))
    aff = json.loads((ROOT / 'data/affiliate.json').read_text(encoding='utf8'))
    AFF = aff
    return data, aff

AFF = {'enabled': False, 'images_enabled': False}

# 단순한 측면 실루엣. 사진은 아니고, 자리만 잡아 레이아웃이 밀리지 않게 한다.
SHOE_SVG = (
    '<svg class="sg-fig-svg" viewBox="0 0 160 120" aria-hidden="true" focusable="false">'
    '<g fill="none" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M26 84c10 6 30 9 54 9 22 0 44-3 54-9 2-1 4-4 3-7-2-9-9-15-20-19"/>'
    '<path d="M117 58c-6-16-22-28-48-28-18 0-33 8-41 20-4 6-6 14-4 22"/>'
    '<path d="M48 53c8-6 22-8 34-2 6 3 10 8 12 14"/>'
    '<path d="M62 55l8 8M70 51l8 8M78 49l8 7"/>'
    '<path d="M32 75c18 4 42 6 74 2"/>'
    '</g></svg>'
)


def images_on(aff=None):
    a = aff if aff is not None else AFF
    return bool(a.get('images_enabled'))


def shoe_figure(s, aff=None, kind='card'):
    """4:3 자리. images_enabled이고 src가 있을 때만 실제 이미지. 지금은 자리만."""
    info = s.get('image') or {}
    alt = (info.get('alt') or f"{s.get('brand_kr') or ''} {s.get('name_kr') or ''}").strip()
    src = (info.get('src') or '').strip() if images_on(aff) else ''
    cls = f'sg-fig sg-fig-{kind}'
    if src:
        return (f'<div class="{cls}">'
                f'<img src="{esc(src)}" alt="{esc(alt)}" width="800" height="600" loading="lazy" decoding="async">'
                f'</div>')
    label = f"{s.get('brand_kr') or ''} {s.get('name_kr') or ''}".strip()
    return (f'<div class="{cls}" role="img" aria-label="{esc(alt)} 사진 자리">'
            f'{SHOE_SVG}<span class="sg-fig-name">{esc(label)}</span></div>')



def won(n):
    if n is None:
        return None
    return f'{int(n):,}원'


def fmt_weight(g, size):
    if g is None:
        return None
    num = str(int(g) if float(g).is_integer() else g)
    if size:
        return f'{num}g ({size} 기준)'
    return f'{num}g (기준 사이즈 공식 미공개)'


def na():
    return '<span class="na">공식 미공개</span>'


def val(v, suffix=''):
    if v is None or v == '':
        return na()
    return esc(f'{v}{suffix}')


def shoe_url(s):
    return f'/shoes/{s["slug"]}.html'


def official_links(s):
    items = [('공식 상품 페이지', s.get('official_url'))]
    if s.get('official_url_womens'):
        items.append(('여성 공식 상품', s['official_url_womens']))
    if s.get('official_url_specs') and s.get('official_url_specs') != s.get('official_url'):
        items.append(('공식 스펙 표기 페이지', s['official_url_specs']))
    if s.get('official_url_editorial'):
        items.append(('공식 제품 소식', s['official_url_editorial']))
    if s.get('official_url_kr') and s.get('official_url_kr') != s.get('official_url'):
        items.append(('한국 공식 스토어', s['official_url_kr']))
    out = []
    for label, url in items:
        if url:
            out.append(f'<a class="ed-link" href="{esc(url)}" rel="noopener noreferrer" target="_blank">{esc(label)}</a>')
    return ' · '.join(out)


def disclosure(aff):
    text = aff.get('disclosure') or ''
    hidden = '' if aff.get('enabled') else ' hidden'
    return f'<aside class="sg-aff" {hidden} data-aff-slot="disclosure">{esc(text)}</aside>'


def buy_slot(s, aff):
    hidden = '' if aff.get('enabled') else ' hidden'
    href = (s.get('affiliate') or {}).get('coupang') if aff.get('enabled') else None
    if href:
        btn = f'<a class="ed-btn" href="{esc(href)}" rel="sponsored noopener noreferrer" target="_blank">구매 링크 (쇼핑몰)</a>'
    else:
        btn = '<span class="ed-btn" aria-disabled="true">구매 링크 (준비 중)</span>'
    return (f'<div class="sg-buy ed-actions" {hidden} data-aff-slot="buy">'
            f'<p class="ed-small">구매 링크의 가격은 쇼핑몰 기준이며, 위 공식 정가와 다를 수 있어요.</p>{btn}</div>')


def crumbs(trail):
    parts = [f'<a href="{h}">{esc(n)}</a><span aria-hidden="true">›</span>' for n, h in trail[:-1]]
    return (f'<div style="padding:20px var(--page-x) 0"><nav class="ed-crumbs" aria-label="현재 위치">'
            f'{"".join(parts)}<span aria-current="page">{esc(trail[-1][0])}</span></nav></div>')


def head(title, desc, path, ld_list, typ='website'):
    url = SITE + path
    ads = hs.adsense_and_ga4(str(ROOT))
    lds = '\n'.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False, separators=(",", ":"))}</script>' for x in ld_list)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<base href="/">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#F6F2EA">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{esc(url)}"><meta property="og:url" content="{esc(url)}">
{ads}
<meta property="og:site_name" content="Run우리"><meta property="og:type" content="{typ}"><meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:image" content="{SITE}/assets/icons/og-image.png">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(desc)}">
<link rel="icon" href="favicon.ico" sizes="48x48"><link rel="icon" href="assets/logo/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="assets/logo/apple-touch-icon.png"><link rel="manifest" href="manifest.webmanifest">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" media="print" onload="this.media='all'">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap"></noscript>
<link rel="stylesheet" href="design-tokens.css"><link rel="stylesheet" href="components.css"><link rel="stylesheet" href="site.css">
{lds}
<script src="app.js"></script></head>'''


def page(title, desc, path, trail, body, ld, typ='website'):
    crumbs_ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': SITE + u} for i, (n, u) in enumerate(trail)]}
    key = 'gear' if path.startswith('/gear') else 'shoes'
    html_doc = (head(title, desc, path, [crumbs_ld] + ld, typ)
                + f'<body class="ed-root"><main class="ed-wrap" id="main"><div id="view">'
                + crumbs(trail) + body + f"</div></main><script>layout('{key}');</script></body></html>\n")
    out = ROOT / path.lstrip('/')
    if path.endswith('/'):
        out = out / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_doc, encoding='utf8')
    return path


def tags(s):
    return ' '.join(f'<span class="sg-tag">{esc(CAT_LABEL.get(c, c))}</span>' for c in s.get('category') or [])


def card(s, aff=None):
    w = fmt_weight(s.get('weight_g'), s.get('weight_size')) or '공식 미공개'
    d = f"{s['drop_mm']}mm" if s.get('drop_mm') is not None else '공식 미공개'
    p = won(s.get('msrp_krw')) or '공식 미공개'
    return (f'<a class="sg-card" href="{shoe_url(s)}">{shoe_figure(s, aff, "card")}'
            f'<div class="br">{esc(s["brand_kr"])}</div>'
            f'<h3>{esc(s["name_kr"])}</h3><div class="sg-facts">'
            f'<span><b>{esc(w)}</b>무게</span><span><b>{esc(d)}</b>드롭</span>'
            f'<span><b>{esc(p)}</b>공식 정가</span></div>'
            f'<p class="ed-small" style="margin:8px 0 0">{tags(s)}</p></a>')


def similar(s, shoes):
    same = [x for x in shoes if x['id'] != s['id'] and set(x.get('category') or []) & set(s.get('category') or [])]
    # prefer same plate/category overlap, cap 4
    same.sort(key=lambda x: (-len(set(x.get('category') or []) & set(s.get('category') or [])), x['name_kr']))
    return same[:4]


def product_ld(s):
    obj = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': f'{s["brand_kr"]} {s["name_kr"]}',
        'brand': {'@type': 'Brand', 'name': s['brand']},
        'url': SITE + shoe_url(s),
        'description': f'{s["brand_kr"]} {s["name_kr"]} 공식 스펙. 확인일 {s["source_checked_on"]}.',
    }
    if s.get('sku'):
        obj['sku'] = s['sku']
    if s.get('official_url'):
        obj['sameAs'] = s['official_url']
    img = (s.get('image') or {}).get('src') if images_on() else None
    if img:
        obj['image'] = img
    if s.get('msrp_krw'):
        obj['offers'] = {
            '@type': 'Offer',
            'priceCurrency': 'KRW',
            'price': str(int(s['msrp_krw'])),
            'url': s.get('official_url') or (SITE + shoe_url(s)),
            'priceSpecification': {'@type': 'UnitPriceSpecification', 'priceType': 'https://schema.org/ListPrice',
                                   'price': str(int(s['msrp_krw'])), 'priceCurrency': 'KRW'},
        }
    # 평점·후기는 넣지 않는다.
    return obj


def item_list_ld(name, url, items):
    return {
        '@context': 'https://schema.org', '@type': 'CollectionPage', 'name': name, 'url': SITE + url, 'inLanguage': 'ko-KR',
        'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(items), 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'url': SITE + shoe_url(s), 'name': f'{s["brand_kr"]} {s["name_kr"]}'}
            for i, s in enumerate(items)
        ]}
    }


def best_filter(key, shoes):
    if key == 'beginner':
        return [s for s in shoes if 'carbon' not in (s.get('category') or []) and s.get('plate') in (None, 'none')
                and (('beginner' in s['category']) or ('daily' in s['category']) or ('stability' in s['category']))]
    if key == 'value':
        return [s for s in shoes if s.get('msrp_krw') is not None and s['msrp_krw'] <= 190000]
    if key == 'daily':
        return [s for s in shoes if 'daily' in s['category']]
    if key == 'max_cushion':
        return [s for s in shoes if 'max_cushion' in s['category']]
    if key == 'tempo':
        return [s for s in shoes if 'tempo' in s['category']]
    if key == 'stability':
        return [s for s in shoes if 'stability' in s['category']]
    if key == 'half':
        return [s for s in shoes if 'carbon' in s['category'] or 'tempo' in s['category']]
    if key == 'marathon':
        return [s for s in shoes if 'carbon' in s['category']]
    if key == 'carbon':
        return [s for s in shoes if s.get('plate') == 'carbon' or 'carbon' in s['category']]
    if key == 'trail':
        return [s for s in shoes if 'trail' in s['category'] or s.get('surface') == 'trail']
    return []


def build_hub(shoes, aff, unverified):
    chips = ''.join(f'<a href="/shoes/best/{k}.html">{esc(lab)}</a>' for k, lab, _ in BEST)
    # sections
    order = ['daily', 'beginner', 'stability', 'max_cushion', 'tempo', 'carbon', 'trail']
    secs = []
    n = 1
    used = set()
    for key in order:
        group = [s for s in shoes if key in (s.get('category') or [])]
        if key == 'beginner':
            group = [s for s in shoes if 'beginner' in s['category']]
        if not group and key != 'trail':
            continue
        inner = ''.join(card(s) for s in group) if group else '<p class="ed-body">이번에 공식 스펙을 확인한 트레일 모델이 아직 없어요. 호카 스피드고트, 아식스 트라부코는 공식 페이지를 이 미리보기에서 열지 못해 목록에 넣지 않았습니다.</p>'
        secs.append(f'<section class="ed-section" id="{key}" style="margin-top:36px"><div class="ed-section-head"><span class="no">{n:02d}</span>'
                    f'<h2 class="ed-h2">{esc(CAT_LABEL.get(key, key))}</h2></div><div class="sg-grid">{inner}</div></section>')
        n += 1
        used.update(s['id'] for s in group)
    body = (f'{disclosure(aff)}<header class="ed-page-head" style="padding:18px var(--page-x) 0">'
            f'<div class="ed-label">러닝화</div><h1 class="ed-h1" style="margin:12px 0 10px">러닝화 공식 스펙 비교</h1>'
            f'<p class="ed-lede">지금 국내에서 살 수 있는 모델을 중심으로, 브랜드 공식 페이지에 적힌 무게·드롭·정가만 모았어요. '
            f'착화감이나 테스트 결과는 짓지 않았고, 공식에 없는 숫자는 ‘공식 미공개’로 비워 두었어요. 확인일 {CHECKED_LABEL} (Asia/Seoul).</p>'
            f'<p class="ed-small">이 목록은 추천 순위가 아니에요. 용도 페이지는 공식 분류·무게·드롭·정가 조건으로만 묶었습니다. '
            f'브랜드 사진은 라이선스 없이 올리지 않았어요. <a class="ed-link" href="/guide/choosing-running-shoes.html">러닝화 고르는 법</a>과 '
            f'<a class="ed-link" href="/gear/">러닝 복장 가이드</a>도 함께 볼 수 있어요.</p>'
            f'<nav class="sg-chips" aria-label="용도별 목록">{chips}</nav></header>'
            + ''.join(secs) +
            f'<p class="ed-small lp-src" style="padding:24px var(--page-x) 8px">스펙은 각 모델 페이지에 출처 URL과 확인일을 적었습니다. '
            f'정가는 공식 정가이며, 지금 사는 값과 다를 수 있어요.</p>')
    title = f'러닝화 공식 스펙 비교 — {len(shoes)}켤레 · 확인일 {CHECKED_LABEL} | Run우리'
    desc = f'공식 브랜드 페이지에서 {CHECKED_LABEL}에 확인한 러닝화 {len(shoes)}켤레의 무게·드롭·정가. 착화감은 짓지 않았고, 없는 값은 공식 미공개로 표시합니다.'
    path = '/shoes/'
    trail = [('Run우리', '/'), ('러닝화', '/shoes/')]
    return page(title, desc, path, trail, body, [item_list_ld(title, path, shoes)])


def build_detail(s, shoes, aff):
    nums = []
    nums.append(('무게', fmt_weight(s.get('weight_g'), s.get('weight_size')) or '공식 미공개',
                 fmt_weight(s.get('weight_g_womens'), s.get('weight_size_womens')) or None))
    nums.append(('드롭', f"{s['drop_mm']}mm" if s.get('drop_mm') is not None else '공식 미공개', None))
    if s.get('stack_heel_mm') is not None or s.get('stack_forefoot_mm') is not None:
        st = f"{s.get('stack_heel_mm') or '—'} / {s.get('stack_forefoot_mm') or '—'}mm"
    else:
        st = '공식 미공개'
    nums.append(('스택(힐/포어)', st, None))
    price = won(s.get('msrp_krw')) or '공식 미공개'
    if s.get('msrp_krw_womens') and s['msrp_krw_womens'] != s.get('msrp_krw'):
        price = f"남성 {won(s['msrp_krw'])} · 여성 {won(s['msrp_krw_womens'])}"
    nums.append(('공식 정가', price, None))
    num_html = ''.join(
        f'<div class="sg-num"><span class="l">{esc(lab)}</span><b>{esc(main)}</b>'
        + (f'<span>여성 {esc(sub)}</span>' if sub else '') + '</div>'
        for lab, main, sub in nums
    )
    plate = {'none': '없음(공식 표기 없음)', 'carbon': '카본(공식 표기)', 'nylon': '나일론(공식 표기)'}.get(s.get('plate') or 'none', s.get('plate'))
    rows = [
        ('브랜드', esc(s['brand_kr'])),
        ('모델', esc(s['name_kr']) + f' <span class="ed-small">({esc(s["name"])})</span>'),
        ('분류', tags(s) or na()),
        ('지면', esc({'road': '로드', 'trail': '트레일'}.get(s.get('surface'), s.get('surface') or '')) or na()),
        ('플레이트', esc(plate)),
        ('남성 무게', esc(fmt_weight(s.get('weight_g'), s.get('weight_size')) or '') or na()),
        ('여성 무게', esc(fmt_weight(s.get('weight_g_womens'), s.get('weight_size_womens')) or '') or na()),
        ('드롭', val(s.get('drop_mm'), 'mm')),
        ('힐 스택', val(s.get('stack_heel_mm'), 'mm')),
        ('포어풋 스택', val(s.get('stack_forefoot_mm'), 'mm')),
        ('미드솔(공식 표기)', esc(s.get('midsole') or '') or na()),
        ('공식 정가', esc(price)),
        ('스타일 번호', esc(s.get('sku') or '') or na()),
        ('판매 상태', '공식몰 기준 현재 모델' if s.get('status') == 'current' else esc(s.get('status'))),
        ('확인일', esc(s.get('source_checked_on'))),
        ('출처', official_links(s)),
    ]
    tr = ''.join(f'<tr><th scope="row">{lab}</th><td>{cell}</td></tr>' for lab, cell in rows)
    notes = ''.join(f'<li>{esc(n)}</li>' for n in (s.get('source_notes') or []))
    sim = similar(s, shoes)
    sim_html = ''.join(card(x) for x in sim)
    body = (f'{disclosure(aff)}<header class="ed-page-head" style="padding:18px var(--page-x) 0">'
            f'<div class="ed-label">{esc(s["brand_kr"])}<span class="ed-sep">·</span>공식 스펙</div>'
            f'<h1 class="ed-h1" style="margin:12px 0 10px">{esc(s["name_kr"])}</h1>'
            f'<p class="ed-lede">{esc(s["brand_kr"])} {esc(s["name_kr"])}의 공식 상품 페이지에 적힌 숫자만 정리했어요. '
            f'착화감·후기·실험실 실측은 짓지 않았습니다. 확인일 {CHECKED_LABEL}.</p>'
            f'<p class="sg-kicker">{tags(s)}</p></header>'
            f'<div class="sg-hero" style="padding:0 var(--page-x)">{shoe_figure(s, aff, "hero")}</div>'
            f'<div style="padding:8px var(--page-x) 0">{num_html}'
            f'<table class="sg-spec"><tbody>{tr}</tbody></table>'
            f'<h2 class="ed-h2">출처와 확인 메모</h2>'
            f'<ul class="ed-body">{notes or "<li>추가 메모 없음.</li>"}</ul>'
            f'<p class="ed-small">정가는 공식 정가(확인일)입니다. 세일가는 ‘지금 사는 값’이 아니라서 적지 않았어요. '
            f'스택·드롭은 브랜드가 페이지에 쓴 값이며, 측정 방법이나 사이즈에 따라 다를 수 있습니다.</p>'
            f'{buy_slot(s, aff)}'
            f'<p class="ed-small" style="margin-top:16px"><a class="ed-link" href="/shoes/">전체 러닝화 목록</a>'
            + ''.join(f' · <a class="ed-link" href="/shoes/best/{c}.html">{esc(CAT_LABEL.get(c, c))}</a>' for c in s.get('category') or [])
            + '</p></div>'
            + (f'<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">02</span>'
               f'<h2 class="ed-h2">비슷한 분류의 모델</h2></div><div class="sg-grid">{sim_html}</div></section>' if sim else '')
            )
    title = f'{s["brand_kr"]} {s["name_kr"]} 공식 스펙 — 무게·드롭·정가 | Run우리'
    w = fmt_weight(s.get('weight_g'), s.get('weight_size')) or '무게 공식 미공개'
    d = f"드롭 {s['drop_mm']}mm" if s.get('drop_mm') is not None else '드롭 공식 미공개'
    desc = f'{s["brand_kr"]} {s["name_kr"]}. {w}, {d}. 공식 페이지 확인일 {CHECKED_LABEL}. 착화감은 적지 않습니다.'
    path = shoe_url(s)
    trail = [('Run우리', '/'), ('러닝화', '/shoes/'), (s['name_kr'], path)]
    return page(title, desc, path, trail, body, [product_ld(s)], typ='product')


def build_best(key, lab, blurb, shoes, aff):
    group = best_filter(key, shoes)
    inner = ''.join(card(s) for s in group) if group else (
        f'<p class="ed-body">이 조건에 맞는, 이번에 공식 스펙을 확인한 모델이 아직 없어요. '
        f'<a class="ed-link" href="/shoes/">러닝화 허브</a>에서 다른 분류를 볼 수 있어요.</p>')
    # simple table too
    thead = '<tr><th>모델</th><th>무게</th><th>드롭</th><th>공식 정가</th></tr>'
    rows = []
    for s in group:
        w = fmt_weight(s.get('weight_g'), s.get('weight_size')) or '공식 미공개'
        d = f"{s['drop_mm']}mm" if s.get('drop_mm') is not None else '공식 미공개'
        p = won(s.get('msrp_krw')) or '공식 미공개'
        rows.append(f'<tr><td><a class="ed-link" href="{shoe_url(s)}">{esc(s["brand_kr"])} {esc(s["name_kr"])}</a></td>'
                    f'<td data-label="무게">{esc(w)}</td><td data-label="드롭">{esc(d)}</td>'
                    f'<td data-label="공식 정가">{esc(p)}</td></tr>')
    table = f'<div class="sg-table-wrap"><table class="sg-cmp"><thead>{thead}</thead><tbody>{"".join(rows)}</tbody></table></div>' if group else ''
    body = (f'{disclosure(aff)}<header class="ed-page-head" style="padding:18px var(--page-x) 0">'
            f'<div class="ed-label">러닝화 · 용도별 목록</div><h1 class="ed-h1" style="margin:12px 0 10px">{esc(lab)}</h1>'
            f'<p class="ed-lede">{esc(blurb)} 확인일 {CHECKED_LABEL}. 추천 랭킹이 아니에요.</p></header>'
            f'<div style="padding:8px var(--page-x) 0">{table}<div class="sg-grid" style="margin-top:12px">{inner}</div>'
            f'<p class="ed-small" style="margin-top:20px"><a class="ed-link" href="/shoes/">러닝화 허브</a></p></div>')
    path = f'/shoes/best/{key}.html'
    title = f'{lab} — 공식 스펙으로 묶은 목록 | Run우리'
    desc = f'{blurb} 확인일 {CHECKED_LABEL}.'
    trail = [('Run우리', '/'), ('러닝화', '/shoes/'), (lab, path)]
    return page(title, desc, path, trail, body, [item_list_ld(lab, path, group)])


def build_compare(a, b, shoes, aff):
    def cell(s, getter):
        return getter(s)
    rows = [
        ('브랜드', lambda s: esc(s['brand_kr'])),
        ('무게', lambda s: esc(fmt_weight(s.get('weight_g'), s.get('weight_size')) or '공식 미공개')),
        ('여성 무게', lambda s: esc(fmt_weight(s.get('weight_g_womens'), s.get('weight_size_womens')) or '공식 미공개')),
        ('드롭', lambda s: val(s.get('drop_mm'), 'mm')),
        ('힐 스택', lambda s: val(s.get('stack_heel_mm'), 'mm')),
        ('포어풋 스택', lambda s: val(s.get('stack_forefoot_mm'), 'mm')),
        ('플레이트', lambda s: esc({'none': '없음', 'carbon': '카본', 'nylon': '나일론'}.get(s.get('plate') or 'none', s.get('plate') or '공식 미공개'))),
        ('미드솔(공식)', lambda s: esc(s.get('midsole') or '공식 미공개')),
        ('공식 정가', lambda s: esc(won(s.get('msrp_krw')) or '공식 미공개')),
        ('확인일', lambda s: esc(s.get('source_checked_on'))),
    ]
    tr = ''.join(
        f'<tr><th scope="row">{lab}</th><td data-label="{esc(a["name_kr"])}">{fn(a)}</td><td data-label="{esc(b["name_kr"])}">{fn(b)}</td></tr>'
        for lab, fn in rows
    )
    body = (f'{disclosure(aff)}<header class="ed-page-head" style="padding:18px var(--page-x) 0">'
            f'<div class="ed-label">러닝화 · 비교</div>'
            f'<h1 class="ed-h1" style="margin:12px 0 10px">{esc(a["name_kr"])} vs {esc(b["name_kr"])}</h1>'
            f'<p class="ed-lede">두 모델의 공식 스펙을 나란히 봤어요. 어느 쪽이 더 편하다거나 기록이 더 나온다는 평가는 적지 않았습니다. 확인일 {CHECKED_LABEL}.</p></header>'
            f'<div style="padding:8px var(--page-x) 0"><div class="sg-cmp-figs">'
            f'<a class="sg-fig-link" href="{shoe_url(a)}">{shoe_figure(a, aff, "cmp")}</a>'
            f'<a class="sg-fig-link" href="{shoe_url(b)}">{shoe_figure(b, aff, "cmp")}</a>'
            f'</div><div class="sg-table-wrap"><table class="sg-cmp"><thead><tr><th>항목</th>'
            f'<th><a class="ed-link" href="{shoe_url(a)}">{esc(a["brand_kr"])} {esc(a["name_kr"])}</a></th>'
            f'<th><a class="ed-link" href="{shoe_url(b)}">{esc(b["brand_kr"])} {esc(b["name_kr"])}</a></th>'
            f'</tr></thead><tbody>{tr}</tbody></table></div>'
            f'<p class="ed-small" style="margin-top:16px">출처는 각 모델 페이지에 있습니다. '
            f'<a class="ed-link" href="/shoes/">러닝화 허브</a></p></div>')
    slug = f'{a["slug"]}-vs-{b["slug"]}'
    path = f'/shoes/compare/{slug}.html'
    title = f'{a["name_kr"]} vs {b["name_kr"]} — 공식 스펙 비교 | Run우리'
    desc = f'{a["brand_kr"]} {a["name_kr"]}와 {b["brand_kr"]} {b["name_kr"]}의 공식 무게·드롭·정가 비교. 확인일 {CHECKED_LABEL}.'
    trail = [('Run우리', '/'), ('러닝화', '/shoes/'), (f'{a["name_kr"]} vs {b["name_kr"]}', path)]
    return page(title, desc, path, trail, body, [])


def inject_internal_links():
    """이미 만들어진 거리·월·가이드·페이스 계산기 페이지에 내부 링크를 넣는다. 원본 running-site는 건드리지 않음."""
    block_dist = {
        'half.html': ('하프 종목이 있는 대회를 보고 계시면, 공식 스펙으로 묶은 <a class="ed-link" href="/shoes/best/half.html">하프 마라톤 러닝화</a>와 '
                      '<a class="ed-link" href="/gear/race-day.html">대회 당일 복장</a>도 함께 볼 수 있어요.'),
        'full.html': ('풀코스 대회와 함께, 공식 스펙으로 묶은 <a class="ed-link" href="/shoes/best/marathon.html">풀코스 러닝화</a>와 '
                      '<a class="ed-link" href="/gear/race-day.html">대회 당일 복장</a>을 볼 수 있어요.'),
        '10k.html': ('10km 대회와 함께 <a class="ed-link" href="/shoes/best/daily.html">데일리 러닝화</a>, '
                     '<a class="ed-link" href="/gear/temperature.html">기온별 복장</a>을 볼 수 있어요.'),
        '5k.html': ('5km 대회와 함께 <a class="ed-link" href="/shoes/best/beginner.html">입문용 러닝화</a>, '
                    '<a class="ed-link" href="/gear/temperature.html">기온별 복장</a>을 볼 수 있어요.'),
    }
    marker = '<!--P3GEAR-->'
    for name, text in block_dist.items():
        p = ROOT / 'distance' / name
        if not p.exists():
            continue
        t = p.read_text(encoding='utf8')
        if marker in t:
            continue
        box = f'<aside class="sg-note"><!--P3GEAR-->{text}</aside>'
        t = t.replace('<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">',
                      box + '<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">', 1)
        p.write_text(t, encoding='utf8')
    winter = {'2026-11.html', '2026-12.html', '2027-01.html', '2027-02.html', '2027-03.html',
              '2026-01.html', '2026-02.html', '2026-03.html'}
    for p in (ROOT / 'month').glob('*.html'):
        t = p.read_text(encoding='utf8')
        if marker in t:
            continue
        if p.name in winter:
            text = ('이 달 대회는 기온이 낮을 수 있어요. <a class="ed-link" href="/gear/winter.html">겨울 러닝복 가이드</a>와 '
                    '<a class="ed-link" href="/gear/temperature.html">기온별 복장</a>을 참고해 주세요.')
        else:
            text = ('대회 당일 옷차림은 <a class="ed-link" href="/gear/temperature.html">기온별 러닝 복장</a>에서 구간별로 볼 수 있어요.')
        box = f'<aside class="sg-note"><!--P3GEAR-->{text}</aside>'
        if 'lp-end' in t:
            t = t.replace('<div class="lp-end">', box + '<div class="lp-end">', 1)
            p.write_text(t, encoding='utf8')
    # guides
    swaps = {
        'guide/choosing-running-shoes.html': (
            'href="blog.html?level=초급"',
            'href="blog.html?level=초급"></a></div>\n      <p class="ed-small" style="margin:8px 0 0"><a class="ed-link" href="/shoes/">공식 스펙으로 본 러닝화 목록</a>도 함께 볼 수 있어요.'
        ),
    }
    # safer guide inject: after lede
    for rel, extra in [
        ('guide/choosing-running-shoes.html', '<p class="ed-small">지금 살 수 있는 모델의 공식 무게·드롭·정가는 <a class="ed-link" href="/shoes/">러닝화 허브</a>에 모아 두었어요.</p>'),
        ('guide/summer-winter-running.html', '<p class="ed-small">기온 구간별 겹쳐 입기는 <a class="ed-link" href="/gear/temperature.html">기온별 러닝 복장</a>, 추운 달 대회는 <a class="ed-link" href="/gear/winter.html">겨울 러닝복</a>을 봐 주세요.</p>'),
        ('guide/first-marathon-checklist.html', '<p class="ed-small">대회 당일 복장과 준비물은 <a class="ed-link" href="/gear/race-day.html">대회 당일 복장 가이드</a>에도 정리했어요.</p>'),
        ('guide/race-gear-checklist.html', '<p class="ed-small">업데이트된 대회 당일 복장 안내는 <a class="ed-link" href="/gear/race-day.html">여기</a>에 있어요.</p>'),
    ]:
        p = ROOT / rel
        if not p.exists():
            continue
        t = p.read_text(encoding='utf8')
        if marker in t or '/shoes/' in t and rel.endswith('choosing-running-shoes.html') and '러닝화 허브' in t:
            continue
        if '</p>\n      </header>' in t:
            t = t.replace('</p>\n      </header>', f'</p>{extra}\n      </header>', 1)
            # mark
            t = t.replace(extra, extra.replace('<p class="ed-small">', f'<p class="ed-small"><!--P3GEAR-->'), 1)
            p.write_text(t, encoding='utf8')
    pace = ROOT / 'tools/pace-calculator.html'
    if pace.exists():
        t = pace.read_text(encoding='utf8')
        if marker not in t:
            note = (f'<aside class="sg-note"><!--P3GEAR-->레이스용과 일상용 신발의 차이는 공식 스펙(무게·드롭·플레이트)으로만 비교할 수 있어요. '
                    f'이 신발을 신으면 기록이 단축된다는 표현은 쓰지 않습니다. '
                    f'<a class="ed-link" href="/shoes/best/daily.html">데일리</a> · '
                    f'<a class="ed-link" href="/shoes/best/carbon.html">카본 러닝화</a></aside>')
            if '<div class="lp-end">' in t:
                t = t.replace('<div class="lp-end">', note + '<div class="lp-end">', 1)
            elif '</main>' in t:
                t = t.replace('</main>', note + '</main>', 1)
            pace.write_text(t, encoding='utf8')
    # race hubs: add pills to existing race-hubs nav (first  and all)
    race_dir = ROOT / 'race'
    added = 0
    if race_dir.exists():
        for p in race_dir.glob('*.html'):
            t = p.read_text(encoding='utf8')
            if marker in t or 'class="ed-section race-hubs"' not in t:
                continue
            extra = ''
            if '하프' in t and 'distance/half.html' in t:
                extra += '<a href="/shoes/best/half.html">하프 러닝화 스펙</a>'
            if '풀코스' in t or 'distance/full.html' in t:
                extra += '<a href="/shoes/best/marathon.html">풀코스 러닝화 스펙</a>'
            extra += '<a href="/gear/temperature.html">기온별 복장</a>'
            t = t.replace('</div></nav>\n</div></main>', extra + f'</div></nav>{marker}\n</div></main>', 1)
            if marker in t:
                p.write_text(t, encoding='utf8')
                added += 1
    return added


def main():
    data, aff = load()
    shoes = data['shoes']
    paths = []
    paths.append(build_hub(shoes, aff, data.get('unverified') or []))
    for s in shoes:
        paths.append(build_detail(s, shoes, aff))
    for key, lab, blurb in BEST:
        paths.append(build_best(key, lab, blurb, shoes, aff))
    by_id = {s['id']: s for s in shoes}
    pairs = [
        ('nike-pegasus-42', 'nike-vomero-18'),
        ('nike-vaporfly-4', 'nike-alphafly-4'),
        ('asics-gel-kayano-33', 'asics-gt-2000-15'),
    ]
    for a, b in pairs:
        if a in by_id and b in by_id:
            paths.append(build_compare(by_id[a], by_id[b], shoes, aff))
    added = inject_internal_links()
    manifest = {'paths': paths, 'shoe_count': len(shoes), 'race_injections': added}
    (ROOT / 'data/p3_urls.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(f'build_shoes: {len(paths)} pages, race injections {added}')


if __name__ == '__main__':
    main()
