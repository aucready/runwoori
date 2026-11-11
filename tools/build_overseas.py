#!/usr/bin/env python3
"""해외 주요 대회 정적 페이지 생성기.

  python3 tools/build_overseas.py   # data/overseas.json → overseas.html + overseas/<slug>.html + data/overseas_pages.json

- 입력: data/overseas.json (각 대회 공식 홈페이지에서 확인한 값만. 비어 있는 항목은 '확인하지 못한 항목')
- 출력: overseas.html(목록), overseas/<slug>.html(대회별), data/overseas_pages.json(sitemap 용)
- 접수 상태는 생성 시점 기준으로 계산한다. tools/daily_publish.sh 가 매일 다시 만든다.
"""
import json, os, re, sys, html, datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weather_lib   # 대회 날씨 예보 표시 (data/weather.json 이 없으면 아무것도 표시하지 않는다)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = os.environ.get('SITE_URL', 'https://runwoori.com').rstrip('/')
TODAY = datetime.datetime.now(ZoneInfo('Asia/Seoul')).date()
WX = weather_lib.load()
WD = ['월', '화', '수', '목', '금', '토', '일']
CC = {'일본': 'JP', '미국': 'US', '영국': 'GB', '호주': 'AU', '독일': 'DE', '대만': 'TW', '프랑스': 'FR', '홍콩': 'HK', '스페인': 'ES'}
TZ = {'일본': '+09:00', '대만': '+08:00', '홍콩': '+08:00'}


def esc(s): return html.escape(str(s), quote=True).replace('&#x27;', "'")
def pd(s): y, m, d = map(int, s.split('-')); return datetime.date(y, m, d)
def wd(d): return WD[d.weekday()]
def full(d): return f'{d.year}.{d.month:02d}.{d.day:02d}({wd(d)})'
def short(d): return f'{d.month}.{d.day}'
def dday(n): return 'D-DAY' if n == 0 else (f'D-{n}' if n > 0 else f'D+{-n}')
def js(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
MUTED = '<span class="muted">공식 페이지에서 확인하지 못했어요</span>'


def read_adsense():
    """내용 페이지의 AdSense + index.html 의 GA4. 얇은 화면(홈·계산기 등)은 소스로 쓰지 않는다."""
    import head_snippets
    return head_snippets.adsense_and_ga4(ROOT)


def prim(r):
    for p in r.get('periods', []):
        if p.get('primary'): return p
    return None


def status(r):
    d = pd(r['date']); end = pd(r.get('end_date') or r['date'])
    if end < TODAY: return ('ended', '종료')
    if r.get('reg_state') == 'full': return ('closed', '정원 마감')       # 공식 사이트가 정원 도달·매진을 알린 대회
    p = prim(r)
    if p:
        s = pd(p['start']) if p.get('start') else None                    # 시작일을 확인하지 못한 접수는 start 를 비워 둔다
        e = pd(p['end']) if p.get('end') else None
        if s and TODAY < s: return ('soon', '접수예정')
        if e is None or TODAY <= e:
            return ('urgent', '마감임박') if (e and (e - TODAY).days <= 10) else ('open', '접수중')
        return ('closed', r.get('reg_label') or '접수 마감')
    if r.get('reg_state') == 'closed': return ('closed', r.get('reg_label') or '접수 마감')
    h = r.get('status_hint')
    return {'open': ('open', '접수중'), 'soon': ('soon', '접수예정'), 'info': ('info', '일정 미공지')}.get(h, ('info', '일정 미공지'))


def reg_line(r):
    p = prim(r); st = status(r)[0]
    if st == 'closed' and r.get('reg_line'): return r['reg_line']
    if p:
        s = pd(p['start']) if p.get('start') else None
        e = pd(p['end']) if p.get('end') else None
        if st == 'soon' and s: return f'{p["label"]} {short(s)} 시작'
        if st in ('open', 'urgent'): return f'{p["label"]} ~{short(e)} (D-{(e - TODAY).days})' if e else f'{p["label"]} 진행 중'
        if st == 'closed': return f'{p["label"]} {short(e)} 마감' if e else f'{p["label"]} 마감'
    return {'open': '접수 진행 중', 'closed': r.get('reg_label') or '접수 마감'}.get(st, '접수 일정 미공지')


def prange(p):
    s = full(pd(p['start'])) if p.get('start') else ''
    e = full(pd(p['end'])) if p.get('end') else ''
    return f'{s} ~ {e}'.strip() if s and e else (f'~ {e}' if e else f'{s} ~')


def meta_line(r): return f'{r["city"]} · {r["country"]}'


def date_txt(r):
    d = pd(r['date'])
    if r.get('end_date'): return f'{full(d)} ~ {full(pd(r["end_date"]))}'
    return full(d)


def desc(r):
    s = f'{r["name"]} · {date_txt(r)} · {r["city"]}({r["country"]})'
    types = [e['type'] for e in r.get('entry', [])]
    if types: s += ' · 참가 방식: ' + '·'.join(types[:3])
    s += '. 공식 홈페이지에서 확인한 일정과 접수 정보.'
    return s if len(s) <= 155 else s[:152].rstrip(' ·,.') + '…'


BM = '<svg viewBox="0 0 18 22" aria-hidden="true"><path d="M3 2.5h12v17.2l-6-4.2-6 4.2z"/></svg>'


def bookmark(id_): return f'<button class="ed-bookmark" aria-pressed="false" aria-label="관심 대회 저장" data-fav="{id_}">{BM}</button>'


def card(r):
    d = pd(r['date']); k, lab = status(r); n = (d - TODAY).days
    cls = '' if k in ('closed', 'ended') else ('soon' if (k == 'urgent' or 0 <= n <= 7) else '')
    chips = ''.join(f'<span class="ed-tag">{esc(e["type"])}</span>' for e in r.get('entry', [])[:3])
    dist = ' · '.join(x['label'].split(' ')[0] + (' ' + x['label'].split(' ')[1] if x['label'].startswith('마라톤') and len(x['label'].split(' ')) > 1 else '') for x in r['distances'][:1])
    return (f'<article class="ed-race" data-id="{r["id"]}"><div class="ed-race-date"><b>{d.day:02d}</b><span>{d.month}월 {wd(d)}</span></div>'
            f'<div class="ed-race-body"><div class="ed-race-top"><span class="ed-status {k}">{lab}</span>{weather_lib.chip(WX, r["id"], TODAY)}</div>'
            f'<h3><a class="row-link" href="overseas/{r["slug"]}.html">{esc(r["name"])}</a></h3>'
            f'<p class="ed-meta">{date_txt(r)}<span class="sep">·</span>{esc(meta_line(r))}</p><p class="ed-meta">{esc(dist)}</p>'
            f'<p class="ed-meta">{esc(reg_line(r))}</p><p class="ov-chips">{chips}</p></div>'
            f'<div class="ed-race-side"><div class="ed-dday {cls}">{dday(n)}</div>{bookmark(r["id"])}</div></article>')


HEAD = '''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<base href="/">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="theme-color" content="#F6F2EA">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{url}"><meta property="og:url" content="{url}">
<!-- Google AdSense -->
{adsense}
<meta property="og:site_name" content="Run우리"><meta property="og:type" content="article"><meta property="og:locale" content="ko_KR">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:image" content="{site}/assets/icons/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{title}"><meta name="twitter:description" content="{desc}"><meta name="twitter:image" content="{site}/assets/icons/og-image.png">
<link rel="icon" href="favicon.ico" sizes="48x48"><link rel="icon" href="assets/logo/favicon.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="assets/logo/apple-touch-icon.png"><link rel="manifest" href="manifest.webmanifest">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" media="print" onload="this.media='all'">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&display=swap"></noscript>
<link rel="stylesheet" href="design-tokens.css"><link rel="stylesheet" href="components.css"><link rel="stylesheet" href="site.css">
{ld}
<script src="app.js"></script></head><body>
'''
TOGGLE = '<nav class="ed-seg ed-seg-link" aria-label="국내·해외 대회 전환"><a href="index.html">국내</a><a class="is-on" href="overseas.html" aria-current="page">해외</a></nav>'
SYNC = '''<script>
layout('overseas');
(function(){
  const sync=()=>{ $$('[data-fav]').forEach(b=>{ const on=favs.has(b.dataset.fav); b.classList.toggle('is-on',on); b.setAttribute('aria-pressed',on); }); $$('.ed-race[data-id]').forEach(c=>c.classList.toggle('is-saved',favs.has(c.dataset.id))); };
  sync(); bindFav();
%s})();
</script></body></html>
'''


def group_label(r): return {'wmm': '월드 마라톤 메이저스', 'more': '그 밖의 해외 마라톤'}.get(r['group'], '한국 러너 인기 대회')


def page(r, others):
    url = f'{SITE}/overseas/{r["slug"]}.html'
    k, lab = status(r); n = (pd(r['date']) - TODAY).days
    title = f'{r["name"]} 일정·참가 방식 | Run우리'
    d = pd(r['date'])
    start = r['date'] + (f'T{r["start_time"]}:00{TZ[r["country"]]}' if r.get('start_time') and r['country'] in TZ else '')
    ld = {'@context': 'https://schema.org', '@type': 'SportsEvent', 'name': r['name'], 'alternateName': r['name_en'], 'description': desc(r),
          'startDate': start, 'endDate': r.get('end_date') or r['date'], 'eventStatus': 'https://schema.org/EventScheduled',
          'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
          'location': {'@type': 'Place', 'name': r.get('venue') or r['city'], 'address': {'@type': 'PostalAddress', 'addressLocality': r['city'], 'addressCountry': CC.get(r['country'], '')}},
          'url': url, 'image': SITE + '/assets/icons/og-image.png', 'inLanguage': 'ko-KR', 'sport': 'Running', 'sameAs': [r['official_url']]}
    crumb = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': '대회 달력', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': '해외 주요 대회', 'item': SITE + '/overseas.html'},
        {'@type': 'ListItem', 'position': 3, 'name': r['name'], 'item': url}]}
    ld_html = f'<script type="application/ld+json">{js(ld)}</script>\n<script type="application/ld+json">{js(crumb)}</script>'
    row = lambda a, b: f'<dt>{a}</dt><dd>{b if b else MUTED}</dd>'
    dist_rows = ''.join(f'<tr><td>{esc(x["label"])}</td><td>{esc(x["note"]) if x["note"] else ""}</td></tr>' for x in r['distances'])
    entry_html = ''.join(f'<div class="ov-entry"><span class="ed-tag">{esc(e["type"])}</span><p>{esc(e["text"])}</p></div>' for e in r.get('entry', []))
    per = r.get('periods', [])
    if per:
        trs = ''.join(f'<tr><td>{esc(p["label"])}</td><td>{prange(p)}<br><span class="muted">{esc(p.get("note",""))}</span></td></tr>' for p in per)
        per_html = f'<table class="ed-table"><thead><tr><th scope="col">구분</th><th scope="col">접수 기간</th></tr></thead><tbody>{trs}</tbody></table>'
    else:
        per_html = '<p class="ed-small">공식 페이지에서 확인된 접수 기간이 없어요. 신청 전에 공식 홈페이지의 최신 공지를 확인하세요.</p>'
    ver = pd(r['verified']); vtxt = f'{ver.year}.{ver.month:02d}.{ver.day:02d}'
    unknown = r.get('unknown') or []
    unk_html = (f'<p class="ed-small" style="line-height:1.8;margin-top:10px">확인하지 못해 비워 둔 항목: {esc(", ".join(unknown))}.</p>' if unknown else '')
    caution = f'<p class="ed-small" style="line-height:1.8;margin-top:10px">{esc(r["caution"])}</p>' if r.get('caution') else ''
    srcs = ' · '.join(f'<a class="ed-link" href="{esc(u)}" target="_blank" rel="noopener noreferrer">{esc(re.sub(r"^https?://(www\\.)?", "", u).split("/")[0])} ↗</a>' for u in r['sources'])
    notes = ''
    if k == 'ended': notes = '<div class="ed-sample race-note"><span class="ed-label">안내</span><span>이 대회는 종료됐어요. 다음 회차 일정은 공식 홈페이지에서 확인하세요.</span></div>'
    oth = ''.join(card(x) for x in others)
    body = f'''<main class="ed-wrap" id="main"><div id="view">
  <div style="padding:20px var(--page-x) 0"><nav class="ed-crumbs" aria-label="현재 위치"><a href="index.html">대회 달력</a><span aria-hidden="true">›</span><a href="overseas.html">해외 주요 대회</a><span aria-hidden="true">›</span><span aria-current="page">{esc(r["name"])}</span></nav></div>
  {notes}
  <header style="padding:18px var(--page-x) 0">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px">
      <div class="ed-race-top"><span class="ed-status {k}">{lab}</span><span class="ed-tag">{group_label(r)}</span></div>
      <div class="ed-dday {'' if k in ('closed','ended') else ('soon' if 0 <= n <= 7 else '')}" style="font-size:34px">{dday(n)}</div></div>
    <h1 class="ed-h1" style="margin:14px 0 4px">{esc(r["name"])}</h1>
    <p class="ed-small" style="margin:0 0 8px;color:var(--ink-3)">{esc(r["name_en"])}</p>
    <p class="ed-lede">{date_txt(r)}{f' · 출발 {esc(r["start_time"])}(현지 시간)' if r.get('start_time') else ''} · {esc(r["city"])}, {esc(r["country"])}</p>
    <div class="ed-actions" style="display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 0">
      <a class="ed-btn" href="{esc(r["official_url"])}" target="_blank" rel="noopener noreferrer">공식 홈페이지 <span class="ed-arrow">↗</span></a>
      <a class="ed-btn ghost" href="{esc(r["entry_url"])}" target="_blank" rel="noopener noreferrer">참가 안내 페이지 <span class="ed-arrow">↗</span></a>
      <button type="button" class="ed-btn ghost ed-savebtn" data-fav="{r["id"]}" aria-pressed="false"><span class="off">북마크 저장</span><span class="on">저장됨</span></button>
    </div>
    {weather_lib.panel(WX, r['id'], TODAY)}
    <p class="ed-small" style="margin-top:14px;line-height:1.7"><b>공식 홈페이지 확인({vtxt})</b> · 확인한 항목: {esc(", ".join(r["checked"]))}.</p>
    <p class="ed-small" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:6px 18px"><button type="button" class="ed-link ed-textbtn" id="ics">캘린더에 추가(.ics)</button><button type="button" class="ed-link ed-textbtn" id="share" hidden>공유</button><button type="button" class="ed-link ed-textbtn" id="copy">링크 복사</button></p>
  </header>
  <div class="ed-cols" style="margin-top:36px">
    <section class="ed-section"><div class="ed-section-head major"><span class="no">01</span><h2 class="ed-h2">대회 정보</h2></div>
      <dl class="ed-dl ov-dl">{row("대회일", date_txt(r))}{row("도시", esc(r["city"]) + ", " + esc(r["country"]))}{row("출발·도착", esc(r.get("venue","")))}{row("출발 시각", esc(r.get("start_time","")) + (" (현지 시간)" if r.get("start_time") else ""))}{row("참가비", esc(r.get("fee","")))}{row("정원", esc(r.get("capacity","")))}{row("제한 시간", esc(r.get("limit","")))}{row("참가 자격", esc(r.get("age","")))}</dl></section>
    <section class="ed-section"><div class="ed-section-head major"><span class="no">02</span><h2 class="ed-h2">접수</h2></div>
      <dl class="ed-dl ov-dl">{row("상태", f'<span class="ed-status {k}">{lab}</span>')}{row("안내", esc(reg_line(r)))}</dl>
      {per_html}</section>
  </div>
  <section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">03</span><h2 class="ed-h2">참가 방식</h2></div>{entry_html}</section>
  <section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">04</span><h2 class="ed-h2">종목</h2></div>
    <table class="ed-table"><thead><tr><th scope="col">종목</th><th scope="col">참고</th></tr></thead><tbody>{dist_rows}</tbody></table></section>
  {f'<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">05</span><h2 class="ed-h2">코스와 특징</h2></div>' + (f'<p class="ed-body" style="line-height:1.85">{esc(r["course"])}</p>' if r.get("course") else '') + (f'<p class="ed-body" style="line-height:1.85;margin-top:10px">{esc(r["highlights"])}</p>' if r.get("highlights") else '') + '</section>' if (r.get("course") or r.get("highlights")) else ''}
  <section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">06</span><h2 class="ed-h2">정보 기준과 확인 방법</h2></div>
    <p class="ed-small" style="line-height:1.8">이 페이지의 값은 {vtxt}에 각 대회 공식 홈페이지에서 직접 확인한 내용이에요. 접수 기간과 참가비는 현지 시간·현지 통화 기준이고, 대회 측 사정으로 바뀔 수 있으니 신청 전에 <a class="ed-link" href="{esc(r["official_url"])}" target="_blank" rel="noopener noreferrer">공식 홈페이지</a>에서 한 번 더 확인하세요.</p>
    {unk_html}{caution}
    <p class="ed-small" style="line-height:1.8;margin-top:10px">확인에 사용한 공식 페이지: {srcs}</p>
    <p class="ed-small" style="line-height:1.8;margin-top:10px">값이 다르거나 빠진 곳을 발견하면 <a class="ed-link" href="contact.html">문의하기</a>로 알려 주세요.</p></section>
  <section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">07</span><h2 class="ed-h2">다른 해외 대회</h2><a class="ed-link" href="overseas.html">모두 보기 →</a></div><div class="ed-list" style="border-top:0">{oth}</div></section>
</div></main>
<script>window.OV={js({"id": r["id"], "name": r["name"], "date": r["date"], "end": r.get("end_date") or r["date"], "venue": r.get("venue") or r["city"], "url": r["official_url"]})};</script>
'''
    extra = '''  $('#ics').onclick=()=>RW.addToCalendar({id:OV.id,name:OV.name,start:OV.date,end:OV.end,date:OV.date,venue:OV.venue,official:OV.url});
  if(RW.native) $('#ics').textContent='캘린더에 추가';
  if(RW.native||navigator.share){ const sb=$('#share'); sb.hidden=false; sb.onclick=()=>RW.share({title:OV.name+' | Run우리',text:OV.name+' 대회 일정',url:location.origin+location.pathname}); }
  $('#copy').onclick=()=>{ const u=location.origin+location.pathname; (navigator.clipboard?navigator.clipboard.writeText(u):Promise.reject()).then(()=>toast('링크를 복사했어요'),()=>toast('복사하지 못했어요. 주소창의 주소를 복사해 주세요')); };
'''
    head = HEAD.format(title=esc(title), desc=esc(desc(r)), url=url, site=SITE, adsense=read_adsense(), ld=ld_html)
    return head + body + SYNC % extra


def hub(races):
    url = f'{SITE}/overseas.html'
    title = '해외 주요 대회 — 월드 마라톤 메이저스·인기 대회 일정 | Run우리'
    d = '도쿄·보스턴·런던·시드니·베를린·시카고·뉴욕과 오사카·나고야·후쿠오카·타이베이 등 해외 마라톤의 일정과 참가 방식을 각 대회 공식 홈페이지 기준으로 정리했어요.'
    wmm = sorted([r for r in races if r['group'] == 'wmm'], key=lambda r: r['date'])
    pop = sorted([r for r in races if r['group'] == 'popular'], key=lambda r: r['date'])
    more = sorted([r for r in races if r['group'] == 'more'], key=lambda r: r['date'])
    items = [{'@type': 'ListItem', 'position': i + 1, 'url': f'{SITE}/overseas/{r["slug"]}.html', 'name': r['name']} for i, r in enumerate(wmm + pop + more)]
    ld = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': '해외 주요 대회', 'itemListElement': items}
    crumb = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': '대회 달력', 'item': SITE + '/'}, {'@type': 'ListItem', 'position': 2, 'name': '해외 주요 대회', 'item': url}]}
    ld_html = f'<script type="application/ld+json">{js(ld)}</script>\n<script type="application/ld+json">{js(crumb)}</script>'
    ver = max(r['verified'] for r in races); vd = pd(ver); vtxt = f'{vd.year}.{vd.month:02d}.{vd.day:02d}'
    openn = [r for r in races if status(r)[0] in ('open', 'urgent')]
    open_html = ''
    if openn:
        open_html = ('<div class="ov-now"><span class="ed-label">지금 신청할 수 있는 대회</span><ul>' + ''.join(
            f'<li><a class="ed-link" href="overseas/{r["slug"]}.html">{esc(r["name"])}</a><span>{esc(reg_line(r))}</span></li>' for r in sorted(openn, key=lambda r: prim(r)['end'] if prim(r) else '9')) + '</ul></div>')
    body = f'''<main class="ed-wrap" id="main">
<div class="landing-title"><h1 class="ed-h1">해외 주요 대회</h1>{TOGGLE}</div>
<p class="ed-lede" style="padding:12px var(--page-x) 0;max-width:46em">월드 마라톤 메이저스 {len(wmm)}개, 한국 러너가 많이 찾는 {len(pop)}개, 그 밖의 일본·스페인 마라톤 {len(more)}개를 담았어요. 값은 모두 각 대회 공식 홈페이지에서 직접 확인했고, 공식 페이지에서 찾지 못한 항목은 추측하지 않고 비워 뒀어요. <span class="muted">(마지막 확인 {vtxt})</span></p>
{open_html}
<section class="ed-section" style="margin-top:28px"><div class="ed-section-head major"><span class="no">01</span><h2 class="ed-h2">월드 마라톤 메이저스</h2><span class="ed-small ed-tab-num"><b style="color:var(--ink)">{len(wmm)}</b>개 · 대회일 순</span></div>
<div class="ed-list" style="border-top:0">{''.join(card(r) for r in wmm)}</div></section>
<section class="ed-section" style="margin-top:36px"><div class="ed-section-head major"><span class="no">02</span><h2 class="ed-h2">한국 러너에게 인기 있는 대회</h2><span class="ed-small ed-tab-num"><b style="color:var(--ink)">{len(pop)}</b>개 · 대회일 순</span></div>
<div class="ed-list" style="border-top:0">{''.join(card(r) for r in pop)}</div></section>
<section class="ed-section" style="margin-top:36px"><div class="ed-section-head major"><span class="no">03</span><h2 class="ed-h2">그 밖의 해외 마라톤</h2><span class="ed-small ed-tab-num"><b style="color:var(--ink)">{len(more)}</b>개 · 대회일 순</span></div>
<div class="ed-list" style="border-top:0">{''.join(card(r) for r in more)}</div></section>
<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">04</span><h2 class="ed-h2">참가 방식, 이렇게 달라요</h2></div>
<dl class="ed-dl ov-dl ov-ways"><dt>추첨</dt><dd>접수 기간 안에 신청한 사람 가운데 무작위로 뽑아요. 기간 안이라면 일찍 신청해도 확률은 같고, 참가비는 보통 당첨된 뒤에 내요.</dd>
<dt>기록 기준</dt><dd>대회가 정한 연령·성별별 기록을 넘은 사람만 신청할 수 있어요. 기준을 넘어도 정원이 차면 떨어질 수 있는 대회도 있어요.</dd>
<dt>자선(채리티)</dt><dd>자선단체를 정해 일정 금액을 모금하거나 기부하는 조건으로 참가권을 받아요. 모금액과 신청 방법은 단체마다 달라요.</dd>
<dt>선착순·패키지</dt><dd>해외 거주자용 선착순 접수나 공식 여행사 패키지에 참가권이 포함된 대회도 있어요.</dd></dl>
<p class="ed-small" style="line-height:1.8;margin-top:12px">일정과 참가비는 대회가 바꿀 수 있어요. 신청 전에는 반드시 각 대회 공식 홈페이지의 최신 공지를 확인하세요.</p></section>
</main>
'''
    head = HEAD.format(title=esc(title), desc=esc(d), url=url, site=SITE, adsense=read_adsense(), ld=ld_html).replace('property="og:type" content="article"', 'property="og:type" content="website"')
    return head + body + SYNC % ''


def main():
    data = json.load(open(os.path.join(ROOT, 'data', 'overseas.json'), encoding='utf8'))
    races = data['races']
    os.makedirs(os.path.join(ROOT, 'overseas'), exist_ok=True)
    for f in os.listdir(os.path.join(ROOT, 'overseas')):
        if f.endswith('.html'): os.remove(os.path.join(ROOT, 'overseas', f))
    pages = []
    for r in races:
        others = [x for x in sorted(races, key=lambda x: x['date']) if x['id'] != r['id'] and x['group'] == r['group']][:3]
        if len(others) < 3: others += [x for x in sorted(races, key=lambda x: x['date']) if x['id'] != r['id'] and x not in others][:3 - len(others)]
        open(os.path.join(ROOT, 'overseas', r['slug'] + '.html'), 'w', encoding='utf8').write(page(r, others))
        pages.append({'slug': r['slug'], 'id': r['id'], 'lastmod': r['verified'], 'ended': status(r)[0] == 'ended'})
    open(os.path.join(ROOT, 'overseas.html'), 'w', encoding='utf8').write(hub(races))
    json.dump({'pages': pages}, open(os.path.join(ROOT, 'data', 'overseas_pages.json'), 'w', encoding='utf8'), ensure_ascii=False)
    print(f'해외 대회 {len(races)}개 → overseas.html + overseas/*.html')


if __name__ == '__main__': main()
