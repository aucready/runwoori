#!/usr/bin/env python3
"""대회별 정적(크롤 가능) 페이지 생성기.

  python3 tools/build_race_pages.py            # data/races.json → race/<id>.html 전부 생성

- 입력: data/races.json (수집기 산출물)  +  data/race_archive.json (지금까지 본 대회 누적본, 이 스크립트가 관리)
- 출력: race/<id>.html (대회마다 1개), data/race_pages.json (sitemap 용 목록), data/race_archive.json
- 지난 대회: 종료 후 180일까지는 '종료' 표시와 함께 색인 허용, 그 이후(또는 수집 목록에서 7일 넘게 사라진 대회)는 noindex + sitemap 제외.
- 종료 후 540일이 지난 기록은 archive 와 race/ 파일에서 삭제.
- 서버 렌더링 내용은 매일 이 스크립트를 돌릴 때 갱신된다(D-day·접수 상태는 생성 시점 기준). tools/daily_publish.sh 참고.
"""
import json, os, re, sys, html, glob, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = os.environ.get('SITE_URL', 'https://runwoori.com').rstrip('/')
KST = ZoneInfo('Asia/Seoul')
TODAY = datetime.datetime.now(KST).date()
URGENT_DAYS = 10
INDEX_DAYS = 180       # 종료 후 이 기간까지는 색인 허용
PRUNE_DAYS = 540       # 종료 후 이 기간이 지나면 기록 삭제
STALE_DAYS = 7         # 수집 목록에서 이만큼 사라진(그리고 아직 안 끝난) 대회는 noindex
WD = ['일', '월', '화', '수', '목', '금', '토']  # JS getDay() 기준(일=0)
PROV = {'서울': '서울특별시', '경기': '경기도', '인천': '인천광역시', '세종': '세종특별자치시', '대전': '대전광역시', '충북': '충청북도',
        '충남': '충청남도', '강원': '강원특별자치도', '부산': '부산광역시', '대구': '대구광역시', '울산': '울산광역시', '경북': '경상북도',
        '경남': '경상남도', '광주': '광주광역시', '전남': '전라남도', '전북': '전북특별자치도', '제주': '제주특별자치도'}


def esc(s):  # app.js esc() 와 동일 (& < > ")
    return html.escape(str(s), quote=True).replace('&#x27;', "'")


def pd(s):
    if not s: return None
    y, m, d = map(int, s.split('-')); return datetime.date(y, m, d)


def wd(d): return WD[(d.weekday() + 1) % 7]
def fmt_full(d): return f'{d.year}.{d.month:02d}.{d.day:02d}({wd(d)})'
def fmt_short(d): return f'{d.month}.{d.day}'
def dday_text(n): return 'D-DAY' if n == 0 else (f'D-{n}' if n > 0 else f'D+{-n}')
def safe_url(u): return u if re.match(r'^https?://', u or '', re.I) else None


def venue_query(v):  # app.js venueQuery() 와 동일
    v = str(v or '')
    q = re.split(r'[(（]', v)[0]
    q = re.split(r'\s[·—–-]\s|·|—', q)[0]
    q = re.sub(r'\s*(일원|일대|집결|옆.*|[A-Z]구역)$', '', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q or v.strip()


def naver_map(v):
    from urllib.parse import quote
    return 'https://map.naver.com/p/search/' + quote(venue_query(v), safe="-_.!~*'()")


# ── app.js 의 adapt / status / regText / feeRange 를 그대로 옮긴 것 ──
def man(n):
    m = n / 10000
    if float(m).is_integer(): return f'{int(m)}만원'
    s = f'{m:.2f}'.rstrip('0'); return f'{float(s):g}만원'


def fee_range(r):
    a, b = r.get('fee_min'), r.get('fee_max')
    if a is None: return ''
    if a == 0 and b == 0: return '무료'
    f = lambda n: man(n) if n >= 10000 and n % 1000 == 0 else f'{n:,}원'
    return f(a) if a == b else f(a) + ' ~ ' + f(b)


def adapt(r):
    start, end = r['date'], r.get('end_date') or r['date']
    ongoing = start < TODAY.isoformat() and end >= TODAY.isoformat()
    dists = r.get('distances') or []
    a = dict(id=r['id'], name=r['name'], start=start, end=end, date=end if ongoing else start, ongoing=ongoing,
             region=r.get('region') or '', venue=r.get('venue') or '', organizer=r.get('organizer') or '', type=r.get('category') or '',
             distances=dists, distTags=r.get('dist_tags') or [], fee=fee_range(r), fee_min=r.get('fee_min'), fee_max=r.get('fee_max'),
             open=r.get('reg_open'), close=r.get('reg_close'), regState=r.get('reg_state'), regNote=r.get('reg_note'),
             official=r.get('official_url'), regUrl=r.get('reg_url'), sources=r.get('sources') or {}, startTime=r.get('start_time'), verified=r.get('verified'))
    a['dist'] = [d['label'] for d in dists]
    race = pd(a['date']); a['d'] = (race - TODAY).days; a['dt'] = race
    a['st'] = status(a)
    return a


def status(r):
    t, race, op, cl = TODAY, pd(r['date']), pd(r['open']), pd(r['close'])
    if race < t: return dict(key='ended', label='종료')
    if r['regState'] == 'full': return dict(key='closed', label='정원 마감')
    if r['regState'] == 'suspended': return dict(key='closed', label='접수 중단')
    if cl and cl < t: return dict(key='closed', label='마감')
    if r['regState'] == 'closed': return dict(key='closed', label='마감')
    if op and op > t: return dict(key='soon', label='접수예정')
    if r['regState'] == 'upcoming': return dict(key='soon', label='접수예정')
    if cl and (cl - t).days <= URGENT_DAYS: return dict(key='urgent', label='마감임박')
    if cl or op or r['regState'] in ('open', 'ongoing'): return dict(key='open', label='접수중')
    return dict(key='info', label='접수 확인')


def reg_text(r):
    t = TODAY
    if r['ongoing']: return f"진행 중 · ~{fmt_short(pd(r['end']))} 까지"
    k = r['st']['key']
    if k == 'soon' and r['open']: return f"접수 {fmt_short(pd(r['open']))} 시작 (D-{(pd(r['open']) - t).days})"
    if k == 'soon': return '접수 예정 · 일정 확인 필요'
    if r['close'] and k != 'closed': return f"접수 ~{fmt_short(pd(r['close']))} (D-{(pd(r['close']) - t).days})"
    if r['close']: return f"접수 마감 {fmt_short(pd(r['close']))}"
    if k == 'closed': return '접수 마감'
    if k == 'info': return '접수 정보 확인 필요'
    return '마감일 확인 필요'


def dday_cls(r):
    if r['st']['key'] in ('closed', 'ended'): return ''
    return 'soon' if (r['st']['key'] == 'urgent' or 0 <= r['d'] <= 7) else ''


BM = '<svg viewBox="0 0 18 22" aria-hidden="true"><path d="M3 2.5h12v17.2l-6-4.2-6 4.2z"/></svg>'
SEP = '<span class="sep">·</span>'


def race_row(r):
    dist = ' · '.join(r['dist'][:3]) + (f" 외 {len(r['dist']) - 3}개" if len(r['dist']) > 3 else '') if r['dist'] else '종목 확인 필요'
    meta1 = SEP.join(x for x in [esc(r['region'] or '지역 확인 필요'), esc(r['type']) if r['type'] else '', esc(dist)] if x)
    fee = r['fee'] or '참가비 확인 필요'
    return (f'<article class="ed-race" data-id="{r["id"]}">'
            f'<div class="ed-race-date"><b>{r["dt"].day:02d}</b><span>{r["dt"].month}월 {wd(r["dt"])}</span></div>'
            f'<div class="ed-race-body"><div class="ed-race-top"><span class="ed-status {r["st"]["key"]}">{r["st"]["label"]}</span></div>'
            f'<h3><a class="row-link" href="race/{r["id"]}.html">{esc(r["name"])}</a></h3>'
            f'<p class="ed-meta">{meta1}</p><p class="ed-meta">{esc(reg_text(r))}{SEP}{esc(fee)}</p></div>'
            f'<div class="ed-race-side"><div class="ed-dday {dday_cls(r)}">{dday_text(r["d"])}</div>'
            f'<button class="ed-bookmark" aria-pressed="false" aria-label="관심 대회 저장" data-fav="{r["id"]}">{BM}</button></div></article>')


def read_snippet(name):
    """index.html 에서 AdSense 등 공통 조각을 읽는다(켜짐/꺼짐 상태가 그대로 따라온다)."""
    s = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
    m = re.search(r'<!--ADSENSE:START-->.*?<!--ADSENSE:END-->', s, re.S)
    return m.group(0) if m else ''


def js(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def description(r):
    parts = [f"{r['name']} · {fmt_full(r['dt'])}"]
    if r['venue']: parts.append(re.split(r'[(（]', r['venue'])[0].strip())
    if r['dist']: parts.append(' · '.join(r['dist'][:3]))
    if r['fee']: parts.append('참가비 ' + r['fee'])
    s = ' · '.join(parts)
    tail = '접수 상태가 지난 대회예요.' if r['st']['key'] == 'ended' else f"접수: {r['st']['label']}. 접수 기간·공식 홈페이지·지도 링크."
    s = f'{s}. {tail}'
    return s if len(s) <= 155 else s[:152].rstrip(' ·,.') + '…'


def json_ld(r, url, official, reg):
    online = '온라인' in r['venue'] or r['region'] == '전국'
    start = r['start'] + (f"T{r['startTime']}:00+09:00" if r['startTime'] and re.match(r'^\d\d:\d\d$', r['startTime']) else '')
    ld = {'@context': 'https://schema.org', '@type': 'SportsEvent', 'name': r['name'], 'description': description(r),
          'startDate': start, 'endDate': r['end'], 'eventStatus': 'https://schema.org/EventScheduled',
          'url': url, 'image': SITE + '/assets/icons/og-image.png', 'inLanguage': 'ko-KR', 'sport': 'Running'}
    if online:
        ld['eventAttendanceMode'] = 'https://schema.org/OnlineEventAttendanceMode'
        ld['location'] = {'@type': 'VirtualLocation', 'url': official or url}
    else:
        ld['eventAttendanceMode'] = 'https://schema.org/OfflineEventAttendanceMode'
        addr = {'@type': 'PostalAddress', 'addressCountry': 'KR'}
        if r['region'] in PROV: addr['addressRegion'] = PROV[r['region']]
        ld['location'] = {'@type': 'Place', 'name': r['venue'] or r['region'] or '장소 미정', 'address': addr}
    if r['organizer']: ld['organizer'] = {'@type': 'Organization', 'name': r['organizer'], **({'url': official} if official else {})}
    if official: ld['sameAs'] = [official]
    avail = {'open': 'InStock', 'urgent': 'InStock', 'soon': 'PreOrder'}.get(r['st']['key'])
    if r['regState'] == 'full': avail = 'SoldOut'
    offers = []
    for d in r['distances']:
        if d.get('fee') is None: continue
        o = {'@type': 'Offer', 'name': d['label'], 'price': d['fee'], 'priceCurrency': 'KRW', 'url': reg or official or url}
        if avail: o['availability'] = 'https://schema.org/' + avail
        if r['open']: o['validFrom'] = r['open']
        if r['close']: o['validThrough'] = r['close']
        offers.append(o)
    if offers: ld['offers'] = offers
    return ld


PREP_POSTS = {  # 거리 구간 → (권장 준비 주수, 읽어 볼 가이드 글)
    '5K':   (8,  [('beginner-5k-plan', '초보자 5km 완주 훈련 계획')]),
    '10K':  (8,  [('10k-training-plan', '10km 대회 준비: 8주 훈련 계획')]),
    '하프': (12, [('half-marathon-prep', '하프마라톤 준비: 12주 훈련 구조')]),
    '풀':   (16, [('marathon-prep-and-taper', '풀코스 준비와 테이퍼링'), ('first-marathon-checklist', '마라톤 첫 참가 준비 순서')]),
}
PREP_COMMON = [('race-gear-checklist', '대회 준비물 점검'), ('race-day-routine', '대회 당일 루틴')]


def longest_tag(r):
    kms = [d.get('km') for d in r['distances'] if d.get('km')]
    if not kms: return None
    k = max(kms)
    return '5K' if k < 7 else '10K' if k < 15 else '하프' if k < 30 else '풀'


def prep_section(r):
    """대회까지 남은 기간 + 가장 긴 종목에 맞춘 안내. 데이터(날짜·거리)로 계산한 문장이라 대회마다 내용이 달라진다."""
    if r['st']['key'] == 'ended' or r['d'] < 0: return ''
    tag = longest_tag(r)
    weeks = r['d'] // 7
    label = {'5K': '5km급', '10K': '10km급', '하프': '하프급', '풀': '풀코스급'}
    posts = list(PREP_COMMON)
    if tag:
        need, ps = PREP_POSTS[tag]
        posts = ps + posts
        longest = max((d.get('km') or 0) for d in r['distances'])
        what = f"가장 긴 종목은 {longest:.1f}km로 {label[tag]}이에요."
        if r['type'] == '트레일' or longest >= 50:
            tip = '산길이나 장거리는 거리보다 시간과 고도가 변수예요. 아래 계획은 평지 기준이니 여유를 더 두세요.'
        elif weeks >= need + 2: tip = f'일반적으로 {need}주 안팎의 준비 기간을 권하는데, 지금은 {weeks}주가 남아 여유가 있어요. 처음 몇 주는 거리를 늘리기보다 규칙적으로 뛰는 습관부터 만드세요.'
        elif weeks >= need - 1: tip = f'일반적으로 {need}주 안팎의 준비 기간을 권해요. 지금부터 시작하면 딱 맞는 일정이에요.'
        elif weeks >= 2: tip = f'일반적으로 {need}주 안팎을 권하는데 남은 기간은 {weeks}주예요. 이미 꾸준히 뛰고 있다면 거리를 무리하게 늘리지 말고 마지막 주 조정에 집중하세요.'
        else: tip = '대회가 가까워서 새로운 훈련을 시작하기엔 늦었어요. 컨디션 관리와 준비물 점검에 시간을 쓰세요.'
    else:
        what = '종목 거리 정보가 아직 없어요.'
        tip = '공식 홈페이지에서 종목과 제한 시간을 먼저 확인한 뒤 훈련 계획을 잡으세요.'
    when = f'대회까지 {r["d"]}일({weeks}주)' if r['d'] >= 7 else f'대회까지 {r["d"]}일'
    links = ''.join(f'<li><a class="ed-link" href="post.html?id={i}">{esc(t)}</a></li>' for i, t in posts)
    return (f'<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">04</span><h2 class="ed-h2">준비 기간 가늠하기</h2></div>'
            f'<p class="ed-small" style="line-height:1.8">{when} 남았어요. {what} {tip}</p>'
            f'<ul class="ed-small" style="line-height:2;margin:10px 0 0 18px;padding:0"><li><a class="ed-link" href="tools.html?date={r["date"]}">이 대회 날짜로 주간 훈련표 만들기</a></li>{links}</ul></section>')


HEAD = '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<base href="/">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#F6F2EA">
<meta name="robots" content="{robots}">
<link rel="canonical" href="{url}"><meta property="og:url" content="{url}">
<!-- Google AdSense -->
{adsense}
<meta property="og:site_name" content="Run우리"><meta property="og:type" content="article"><meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:image" content="{site}/assets/icons/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Run우리 — 마라톤·러닝 대회 일정">
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


def build_page(r, related, rec, indexable, stale, adsense):
    url = f"{SITE}/race/{r['id']}.html"
    official, reg = safe_url(r['official']), safe_url(r['regUrl'])
    ended = r['st']['key'] == 'ended'
    title = f"{r['name']} 접수·일정·코스 | Run우리"
    desc = description(r)
    date_txt = f"{fmt_full(pd(r['start']))} ~ {fmt_full(pd(r['end']))}" if r['start'] != r['end'] else fmt_full(r['dt'])
    if r['open'] or r['close']:
        reg_period = f"{fmt_full(pd(r['open'])) if r['open'] else '시작일 미확인'} ~ {fmt_full(pd(r['close'])) if r['close'] else '정원 마감 시까지'}"
    else: reg_period = r['regNote'] or ''
    row = lambda k, v, cls='': f'<dt>{k}</dt><dd class="{cls}">{v or "<span class=\"muted\">확인 필요</span>"}</dd>'
    if r['distances']:
        trs = ''.join('<tr><td>%s</td><td style="text-align:right">%s</td></tr>' % (esc(d['label']),
              '<span class="muted">확인 필요</span>' if d.get('fee') is None else ('무료' if d['fee'] == 0 else f"{d['fee']:,}원")) for d in r['distances'])
        dists = f'<table class="ed-table"><thead><tr><th scope="col">종목</th><th scope="col" style="text-align:right">참가비</th></tr></thead><tbody>{trs}</tbody></table>'
    else: dists = '<p class="ed-small">종목 정보가 아직 없어요. 공식 홈페이지에서 확인하세요.</p>'
    src = ' · '.join(f'<a class="ed-link" href="{esc(u)}" target="_blank" rel="noopener noreferrer">KorMarathon ↗</a>' for k, u in r['sources'].items() if k == 'kormarathon')
    region = r['region']
    crumbs_html = (f'<nav class="ed-crumbs" aria-label="현재 위치"><a href="index.html">대회 달력</a><span aria-hidden="true">›</span>'
                   + (f'<a href="index.html?region={quote(region)}">{esc(region)}</a><span aria-hidden="true">›</span>' if region else '')
                   + f'<span aria-current="page">{esc(r["name"])}</span></nav>')
    crumb_ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': '대회 달력', 'item': SITE + '/'}]
        + ([{'@type': 'ListItem', 'position': 2, 'name': region, 'item': f'{SITE}/?region={quote(region)}'}] if region else [])
        + [{'@type': 'ListItem', 'position': 3 if region else 2, 'name': r['name'], 'item': url}]}
    notes = ''
    if ended:
        notes += '<div class="ed-sample race-note"><span class="ed-label">안내</span><span>이 대회는 종료됐어요. 다음 회차 일정은 <a class="ed-link" href="index.html">대회 달력</a>에서 확인하세요.</span></div>'
    elif stale:
        notes += '<div class="ed-sample race-note"><span class="ed-label">안내</span><span>최근 수집 목록에서 이 대회가 확인되지 않아요. 일정이 바뀌었거나 취소됐을 수 있으니 공식 홈페이지를 확인하세요.</span></div>'
    naver = (f'<a class="ed-link" href="{naver_map(r["venue"])}" target="_blank" rel="noopener noreferrer">네이버 지도에서 장소 보기 ↗</a>'
             if r['venue'] and '온라인' not in r['venue'] else '')
    rel_html = ''
    n_rel = '06' if (r['st']['key'] != 'ended' and r['d'] >= 0) else '05'
    if related:
        rel_html = (f'<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">{n_rel}</span>'
                    f'<h2 class="ed-h2">{esc(region)} 지역의 다른 대회</h2><a class="ed-link" href="index.html?region={quote(region)}">모두 보기 →</a></div>'
                    f'<div class="ed-list" style="border-top:0">{"".join(race_row(x) for x in related)}</div></section>')
    updated = datetime.datetime.now(KST).strftime('%Y.%m.%d')
    ver = r.get('verified')
    ver_txt = ''
    if ver:
        vd = pd(ver['date']); vtxt = f'{vd.year}.{vd.month:02d}.{vd.day:02d}'
        flds = ', '.join(ver.get('fields') or [])
        ver_txt = f'공식 홈페이지 확인 완료({vtxt})'
        ver_badge = (f'<p class="ed-small" style="margin-top:14px;line-height:1.7"><b>{ver_txt}</b>'
                     + (f' · 확인한 항목: {esc(flds)}' if flds else '') + '. 나머지 항목은 수집 정보라 공식 안내와 다를 수 있어요.</p>')
    else: ver_badge = ''
    if official:
        official_note = ('<p class="ed-small" style="margin-top:14px;line-height:1.7">정보는 각 대회 공식 안내를 기준으로 정리해요. 일정·참가비·접수 기간은 바뀔 수 있으니 '
                         f'신청 전에 <a class="ed-link" href="{esc(official)}" target="_blank" rel="noopener noreferrer">공식 홈페이지</a>에서 한 번 더 확인하세요.</p>')
    else:
        official_note = ('<p class="ed-small" style="margin-top:14px;line-height:1.7">공식 홈페이지 주소를 아직 찾지 못했어요. 정보는 각 대회 공식 안내가 기준이니, '
                         f'대회 이름으로 검색해 주최 측 공지를 확인한 뒤 신청하세요. 주소를 아시면 <a class="ed-link" href="contact.html">알려 주세요</a>.</p>')
    prep_html = prep_section(r)
    n_src = '05' if prep_html else '04'
    body = f'''<main class="ed-wrap" id="main"><div id="view">
  <div style="padding:20px var(--page-x) 0">{crumbs_html}</div>
  {notes}
  <header style="padding:18px var(--page-x) 0">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px">
      <div class="ed-race-top"><span class="ed-status {r['st']['key']}">{r['st']['label']}</span>{f'<span class="ed-tag">{esc(r["type"])}</span>' if r['type'] else ''}</div>
      <div class="ed-dday {dday_cls(r)}" style="font-size:34px">{'진행 중' if r['ongoing'] else dday_text(r['d'])}</div></div>
    <h1 class="ed-h1" style="margin:14px 0 8px">{esc(r['name'])}</h1>
    <p class="ed-lede">{date_txt}{f" · 출발 {esc(r['startTime'])}" if r['startTime'] else ''}{f" · {esc(r['venue'])}" if r['venue'] else ''}{f" ({esc(region)})" if region else ''}</p>
    <div class="ed-actions" style="display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 0">
      {f'<a class="ed-btn" href="{esc(official)}" target="_blank" rel="noopener noreferrer">공식 홈페이지 <span class="ed-arrow">↗</span></a>' if official else ''}
      {f'<a class="ed-btn ghost" href="{esc(reg)}" target="_blank" rel="noopener noreferrer">접수 페이지 <span class="ed-arrow">↗</span></a>' if reg else ''}
      <button type="button" class="ed-btn ghost ed-savebtn" data-fav="{r['id']}" aria-pressed="false"><span class="off">북마크 저장</span><span class="on">저장됨</span></button>
    </div>
    {ver_badge}{official_note}
    <p class="ed-small" style="margin-top:14px;display:flex;flex-wrap:wrap;gap:6px 18px">
      <a class="ed-link" href="tools.html?date={r['date']}">이 대회로 훈련 계획 만들기</a>
      <button type="button" class="ed-link ed-textbtn" id="ics">캘린더에 추가(.ics)</button>
      <button type="button" class="ed-link ed-textbtn" id="copy">링크 복사</button>
      {naver}</p>
  </header>
  <div class="ed-cols" style="margin-top:36px">
    <section class="ed-section"><div class="ed-section-head major"><span class="no">01</span><h2 class="ed-h2">대회 정보</h2></div>
      <dl class="ed-dl">{row('대회일', date_txt, 'serif')}{row('장소', esc(r['venue']))}{row('지역', esc(region))}{row('주최', esc(r['organizer']))}{row('출발', esc(r['startTime'] or ''))}{row('참가비', esc(r['fee']))}</dl></section>
    <section class="ed-section"><div class="ed-section-head major"><span class="no">02</span><h2 class="ed-h2">접수</h2></div>
      <dl class="ed-dl">{row('상태', f'<span class="ed-status {r["st"]["key"]}">{r["st"]["label"]}</span>')}{row('접수 기간', esc(reg_period))}{row('안내', esc(reg_text(r)))}</dl>
      {f'<p class="ed-small" style="margin-top:8px">원문 표기: {esc(r["regNote"])}</p>' if r['regNote'] and (r['open'] or r['close']) else ''}</section>
  </div>
  <section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">03</span><h2 class="ed-h2">종목 · 참가비</h2></div>{dists}</section>
  {prep_html}
  <section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">{n_src}</span><h2 class="ed-h2">정보 기준과 확인 방법</h2></div>
    <p class="ed-small" style="line-height:1.8">대회 정보의 기준은 {f'<a class="ed-link" href="{esc(official)}" target="_blank" rel="noopener noreferrer">대회 공식 홈페이지</a>' if official else '대회 공식 안내'}예요. 참가비와 접수 기간, 출발 시각은 주최 측 공지가 우선하고, 이 페이지는 {updated}에 정리한 내용이에요.<br>
    값이 다르거나 빠진 곳을 발견하면 <a class="ed-link" href="contact.html">문의하기</a>로 알려 주세요. 확인되는 대로 고쳐요.{f'<br><span class="muted">수집 참고: {src}</span>' if src else ''}{f'<br>{ver_txt}: <a class="ed-link" href="{esc(ver["url"])}" target="_blank" rel="noopener noreferrer">확인한 공식 페이지 ↗</a>' if ver else ''}</p></section>
  {rel_html}
</div></main>
<script>window.RACE_REC={js(rec)};</script>
<script>
layout('races');
(function(){{
  const r=enrich(adapt(window.RACE_REC));
  const sync=()=>{{ $$('[data-fav]').forEach(b=>{{ const on=favs.has(b.dataset.fav); b.classList.toggle('is-on',on); b.setAttribute('aria-pressed',on); }}); $$('.ed-race[data-id]').forEach(c=>c.classList.toggle('is-saved',favs.has(c.dataset.id))); }};
  sync(); bindFav();
  $('#ics').onclick=()=>downloadText(r.id+'.ics',raceIcs([r]),'text/calendar');
  $('#copy').onclick=()=>{{ const u=location.origin+location.pathname; (navigator.clipboard?navigator.clipboard.writeText(u):Promise.reject()).then(()=>toast('링크를 복사했어요'),()=>toast('복사하지 못했어요. 주소창의 주소를 복사해 주세요')); }};
}})();
</script></body></html>
'''
    head = HEAD.format(title=esc(title), desc=esc(desc), robots='index,follow' if indexable else 'noindex,follow', url=url, site=SITE,
                       adsense=adsense, ld=js(json_ld(r, url, official, reg)), crumbs=js(crumb_ld))
    return head + body


def main():
    src = json.load(open(os.path.join(ROOT, 'data', 'races.json'), encoding='utf8'))
    fetched = (src.get('fetched_at') or '')[:10] or TODAY.isoformat()
    arch_p = os.path.join(ROOT, 'data', 'race_archive.json')
    archive = json.load(open(arch_p, encoding='utf8')) if os.path.exists(arch_p) else {}
    current = set()
    for rec in src['races']:
        archive[rec['id']] = {**rec, '_last_seen': fetched}
        current.add(rec['id'])
    # 오래 지난 기록 정리
    for rid in list(archive):
        end = pd(archive[rid].get('end_date') or archive[rid]['date'])
        if (TODAY - end).days > PRUNE_DAYS: del archive[rid]
    races = {rid: adapt({k: v for k, v in rec.items() if k != '_last_seen'}) for rid, rec in archive.items()}
    adsense = read_snippet('adsense')
    out_dir = os.path.join(ROOT, 'race'); os.makedirs(out_dir, exist_ok=True)
    pages, written = [], set()
    for rid, r in sorted(races.items(), key=lambda kv: kv[1]['date']):
        rec = {k: v for k, v in archive[rid].items() if k != '_last_seen'}
        last_seen = archive[rid].get('_last_seen', fetched)
        ended = r['st']['key'] == 'ended'
        days_after = (TODAY - pd(r['end'])).days if ended else -1
        stale = (rid not in current) and not ended and (TODAY - pd(last_seen)).days > STALE_DAYS
        indexable = not stale and (not ended or days_after <= INDEX_DAYS)
        cand = [x for x in races.values() if x['id'] != rid and x['st']['key'] != 'ended' and x['d'] >= 0 and r['region'] and x['region'] == r['region']
                and x['id'] in current]
        cand.sort(key=lambda x: (x['date'][:7] != r['date'][:7], abs(x['d'] - r['d'])))
        page = build_page(r, cand[:4], rec, indexable, stale, adsense)
        with open(os.path.join(out_dir, rid + '.html'), 'w', encoding='utf8') as f: f.write(page)
        written.add(rid + '.html')
        pages.append({'id': rid, 'url': f'{SITE}/race/{rid}.html', 'lastmod': last_seen if ended or rid not in current else fetched, 'indexable': indexable, 'ended': ended})
    for f in glob.glob(os.path.join(out_dir, '*.html')):
        if os.path.basename(f) not in written: os.remove(f)
    json.dump(archive, open(arch_p, 'w', encoding='utf8'), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump({'generated': TODAY.isoformat(), 'pages': pages}, open(os.path.join(ROOT, 'data', 'race_pages.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    n_idx = sum(p['indexable'] for p in pages)
    print(f'race pages: {len(pages)}개 (색인 {n_idx} · noindex {len(pages) - n_idx}) → race/<id>.html · 지난 대회 {sum(p["ended"] for p in pages)}개')


if __name__ == '__main__':
    main()
