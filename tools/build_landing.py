#!/usr/bin/env python3
"""자동 갱신 랜딩 페이지 생성기 (마감 임박 · 월별 · 지역별).

  python3 tools/build_landing.py

- 입력: data/races.json (KorMarathon 수집 + data/official_overrides.json 공식 확인값), data/race_archive.json, data/race_pages.json
        (러닝온 등 다른 출처는 쓰지 않는다)
- 출력: deadline.html, month/<YYYY-MM>.html, region/<slug>.html, data/landing_pages.json(sitemap 용),
        index.html 안의 <!--LANDING:START-->…<!--LANDING:END--> 모아보기 링크 블록
- 얇은 페이지 방지: 한 페이지에 대회가 MIN_*개 미만이면 만들지 않는다(마감 임박은 만들되 noindex·사이트맵 제외).
- tools/daily_publish.sh 가 매일 build_race_pages.py 다음에 실행한다(D-day·접수 상태는 생성 시점 기준).
"""
import json, os, re, sys, html, datetime, collections, hashlib
sys.path.insert(0, os.path.dirname(__file__))
import build_race_pages as brp
import build_overseas as bo
from hubs import MIN_MONTH, MIN_REGION, MIN_HUB, REGIONS, DISTS, months_of, month_keys, region_keys, year_keys, dist_indexable   # 허브 기준은 hubs.py 한 곳에서

ROOT = brp.ROOT; SITE = brp.SITE; TODAY = brp.TODAY
MIN_DEADLINE = 5      # 마감 임박 페이지: 목록(7일 내 + 이어지는 마감) 최소
esc = brp.esc
SEP = brp.SEP
WDK = ['월', '화', '수', '목', '금', '토', '일']   # date.weekday() 기준


def kd(d): return f'{d.month}/{d.day}({WDK[d.weekday()]})'
def ks(s): d = brp.pd(s); return f'{d.month}/{d.day}({WDK[d.weekday()]})'

def month_overlap(r, key):
    return r['start'][:7] <= key <= r['end'][:7]

def week_overlap(r, y, m, a, b, last):
    s, e = brp.pd(r['start']), brp.pd(r['end'])
    return s <= datetime.date(y, m, min(b, last)) and e >= datetime.date(y, m, a)


# ── 안내 문구 ─────────────────────────────────────────────────────
# 공식 근거 없는 사실 주장(기후·지형·특정 장소·통계 등)은 쓰지 않는다.
# 문장은 (1) data/races.json 에서 계산되는 값, (2) "공식 안내에서 확인하세요" 형태의 확인 요청만 쓴다.
def weekday_sentence(L):
    c = collections.Counter(brp.pd(r['date']).weekday() for r in L)
    if not c: return ''
    top = ', '.join(f'{WDK[k]}요일 {v}개' for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:3])
    return f'요일별로 대회 수가 많은 순서는 {top}예요.'


CSS_MARK = '/* landing */'


def read_races():
    src = json.load(open(os.path.join(ROOT, 'data', 'races.json'), encoding='utf8'))
    pp = os.path.join(ROOT, 'data', 'prior_year.json')
    brp.PRIOR = json.load(open(pp, encoding='utf8')) if os.path.exists(pp) else {}
    cur = {r['id']: brp.adapt(r) for r in src['races']}
    # 월별 페이지용: 종료 대회까지 포함한 누적본 중 색인 허용 + 현재 목록에 있거나 이미 끝난 것
    arch = json.load(open(os.path.join(ROOT, 'data', 'race_archive.json'), encoding='utf8'))
    pages = {p['id']: p for p in json.load(open(os.path.join(ROOT, 'data', 'race_pages.json'), encoding='utf8'))['pages']}
    allr = {}
    for rid, rec in arch.items():
        if not pages.get(rid, {}).get('indexable'): continue
        allr[rid] = cur.get(rid) or brp.adapt({k: v for k, v in rec.items() if k != '_last_seen'})
    fetched = (src.get('fetched_at') or '')[:10]
    return cur, allr, fetched


def rows(lst): return ''.join(brp.race_row(r) for r in lst)


def list_hash(*lists):
    """목록에 든 대회와 각 대회의 접수 상태로 만든 해시 — sitemap lastmod 는 이게 바뀐 날만 갱신(build_sitemap.py)."""
    key = '|'.join(f"{r['id']}:{r['st']['key']}:{r['date']}" for lst in lists for r in lst)
    return hashlib.sha1(key.encode('utf8')).hexdigest()[:16]


def head(title, desc, url, ld_html):
    h = bo.HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, adsense=bo.read_adsense(), ld=ld_html)
    return h.replace('property="og:type" content="article"', 'property="og:type" content="website"')


def tail(): return bo.SYNC.replace("layout('overseas')", "layout('races')") % ''


def ld_for(name, url, crumbs, lst):
    items = [{'@type': 'ListItem', 'position': i + 1, 'url': f'{SITE}/race/{r["id"]}.html', 'name': r['name']} for i, r in enumerate(lst[:50])]
    cp = {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': name, 'url': url, 'inLanguage': 'ko-KR',
          'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(lst), 'itemListElement': items}}
    bc = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': u} for i, (n, u) in enumerate(crumbs)]}
    return f'<script type="application/ld+json">{brp.js(cp)}</script>\n<script type="application/ld+json">{brp.js(bc)}</script>'


def crumbs_html(trail):
    parts = [f'<a href="{h}">{esc(n)}</a><span aria-hidden="true">›</span>' for n, h in trail[:-1]]
    return f'<div style="padding:20px var(--page-x) 0"><nav class="ed-crumbs" aria-label="현재 위치">{"".join(parts)}<span aria-current="page">{esc(trail[-1][0])}</span></nav></div>'


def section(no, title, inner, major=False, more=None):
    m = f'<a class="ed-link" href="{more[0]}">{esc(more[1])} →</a>' if more else ''
    return (f'<section class="ed-section" style="margin-top:36px"><div class="ed-section-head{" major" if major else ""}"><span class="no">{no:02d}</span>'
            f'<h2 class="ed-h2">{esc(title)}</h2>{m}</div>{inner}</section>')


def para(t, extra=''): return f'<p class="ed-body lp-p"{extra}>{t}</p>'


def stamp(fetched):
    d = brp.pd(fetched) if fetched else TODAY
    return (f'<p class="ed-small lp-src">이 페이지는 하루 한 번 자동으로 다시 만들어져요(마지막 갱신 {TODAY.year}.{TODAY.month:02d}.{TODAY.day:02d} · 대회 데이터 수집 {d.year}.{d.month:02d}.{d.day:02d}). '
            f'대회 정보는 <a class="ed-link" href="https://www.kormarathon.com" target="_blank" rel="noopener noreferrer">KorMarathon</a>의 공개 정보와 대회 공식 홈페이지에서 확인한 값만 사용해요. '
            f'일정·참가비·접수 기간은 바뀔 수 있으니 신청 전에 각 대회 공식 홈페이지를 꼭 확인하세요. 틀린 내용을 발견하면 <a class="ed-link" href="contact.html">문의하기</a>로 알려 주세요.</p>')


NAVX = {'years': [], 'dists': [], 'open': False}   # main() 에서 채움: 색인되는 연도·거리·접수 중 허브


def nav_block(months, regions, here):
    def a(href, label, key, _here=here):
        classes = (['ed-link', 'act'] if key == 'deadline' else []) + (['is-on'] if key == _here else [])
        attr = (' aria-current="page"' if key == _here else '') + (f' class="{" ".join(classes)}"' if classes else '')
        return f'<a href="{href}"{attr}>{esc(label)}</a>'
    # 해가 바뀌는 달은 연도를 붙인다(10월 11월 12월 2027년 1월 …)
    ml = ''.join(a(f'month/{m}.html', (f'{int(m[:4])}년 {int(m[5:])}월' if i and m[:4] != months[i - 1][:4] else f'{int(m[5:])}월'), 'm' + m) for i, m in enumerate(months))
    rl = ''.join(a(f'region/{REGIONS[g]}.html', g, 'r' + g) for g in regions)
    out = f'<div class="lp-links-row"><span class="ed-label">마감</span>{a("deadline.html", "마감 임박", "deadline")}</div>'
    if NAVX['open']: out = out.replace('<span class="ed-label">마감</span>', '<span class="ed-label">접수</span>' + a('open.html', '접수 중', 'open'), 1)
    if NAVX['years']: out += '<div class="lp-links-row"><span class="ed-label">연도</span>' + ''.join(a(f'marathon-schedule/{y}.html', f'{y} 일정', 'y' + y) for y in NAVX['years']) + '</div>'
    if ml: out += f'<div class="lp-links-row"><span class="ed-label">월별</span>{ml}</div>'
    if rl: out += f'<div class="lp-links-row"><span class="ed-label">지역별</span>{rl}</div>'
    if NAVX['dists']: out += '<div class="lp-links-row"><span class="ed-label">거리별</span>' + ''.join(a(f'distance/{sl}.html', lab, 'd' + sl) for sl, lab in NAVX['dists']) + '</div>'
    return f'<nav class="lp-links" aria-label="대회 모아보기">{out}</nav>'


# ── 마감 임박 ────────────────────────────────────────────────────
def build_deadline(cur, fetched, months, regions):
    R = [r for r in cur.values() if r['st']['key'] in ('open', 'urgent') and r['close']]
    for r in R: r['cd'] = (brp.pd(r['close']) - TODAY).days
    wk = sorted([r for r in R if 0 <= r['cd'] <= 7], key=lambda r: (r['close'], r['date']))
    nx = sorted([r for r in R if 8 <= r['cd'] <= 21], key=lambda r: (r['close'], r['date']))
    soon = sorted([r for r in cur.values() if r['st']['key'] == 'soon' and r['open'] and 0 <= (brp.pd(r['open']) - TODAY).days <= 14], key=lambda r: (r['open'], r['date']))
    unk = [r for r in cur.values() if r['st']['key'] == 'info']
    indexable = len(wk) + len(nx) >= MIN_DEADLINE
    url = f'{SITE}/deadline.html'
    end = TODAY + datetime.timedelta(days=7)
    title = f'이번 주 접수 마감 대회 ({TODAY.month}/{TODAY.day}~{end.month}/{end.day}) {len(wk)}개 | Run우리'
    if wk:
        first = wk[0]
        d = f'오늘({TODAY.month}/{TODAY.day})부터 7일 안에 접수가 끝나는 마라톤·러닝 대회 {len(wk)}개. 가장 빠른 마감은 {ks(first["close"])} {first["name"]}. 접수 마감일 순 정리.'
    else:
        d = f'오늘({TODAY.month}/{TODAY.day})부터 7일 안에 마감되는 대회는 없어요. 그다음으로 마감되는 대회와 곧 접수가 시작되는 대회를 마감일 순으로 정리했어요.'
    if len(d) > 155: d = d[:152].rstrip(' ·,.') + '…'
    by_close = collections.Counter(r['close'] for r in wk)
    if wk:
        peak = by_close.most_common(1)[0]
        lede = (f'{TODAY.month}월 {TODAY.day}일({WDK[TODAY.weekday()]}) 기준으로 7일 안에 접수가 끝나는 대회는 <b>{len(wk)}개</b>예요. '
                f'마감일이 가장 많이 몰린 날은 {ks(peak[0])}로 {peak[1]}개 대회가 같은 날 접수를 닫아요. 목록은 접수 마감일이 빠른 순서예요. 카드 오른쪽의 D-숫자는 대회까지 남은 날이고, 접수 마감까지 남은 날은 카드 안의 ‘접수 ~월.일 (D-숫자)’로 볼 수 있어요.')
    else:
        lede = f'{TODAY.month}월 {TODAY.day}일({WDK[TODAY.weekday()]}) 기준으로 7일 안에 마감되는 대회는 없어요. 아래에서 그다음으로 마감되는 대회를 확인하세요.'
    secs = []; n = 1
    secs.append(section(n, '7일 안에 마감되는 대회', f'<div class="ed-list" style="border-top:0">{rows(wk)}</div>' if wk else para('지금은 7일 안에 마감되는 대회가 없어요.'), major=True)); n += 1
    if nx:
        secs.append(section(n, '그다음 2주 안에 마감되는 대회', f'<div class="ed-list" style="border-top:0">{rows(nx)}</div>')); n += 1
    if soon:
        secs.append(section(n, '곧 접수가 시작되는 대회', para('2주 안에 접수가 시작되는 대회예요. 접수 시작일과 시각은 공식 홈페이지 공지를 확인하세요.') + f'<div class="ed-list" style="border-top:0">{rows(soon)}</div>')); n += 1
    guide = ''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a, b in [
        ('마감일 확인', '목록의 마감일은 참고용이에요. 종목별 마감일, 정원 마감 여부, 마감 시각은 대회 공식 접수 페이지의 표시를 기준으로 확인하세요.'),
        ('결제까지 확인', '접수 완료 조건(참가비 결제·입금 기한 등)은 대회마다 달라요. 공식 접수 안내에서 확인하세요.'),
        ('단체·기념품', '단체 접수나 기념품 선택에 별도 일정이 있는지는 공식 안내의 세부 일정을 확인하세요.'),
        ('일정 미공지 대회', f'접수 일정이 아직 공개되지 않은 대회는 {len(unk)}개예요. 이런 대회는 공식 홈페이지 공지를 확인해 주세요.'),
    ])
    secs.append(section(n, '마감이 임박한 대회, 신청 전에 이것만 확인하세요', f'<dl class="ed-dl ov-dl ov-ways">{guide}</dl>')); n += 1
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html([("대회 달력", "/"), ("마감 임박 대회", "deadline.html")])}'
            f'<div class="landing-title"><h1 class="ed-h1">이번 주 접수 마감 대회</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{len(wk)}</b>개 · 마감일 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "deadline")}'
            f'{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for('이번 주 접수 마감 대회', url, [('대회 달력', SITE + '/'), ('마감 임박 대회', url)], wk + nx)
    html_ = head(title, d, url, ld) + body + tail()
    if not indexable: html_ = html_.replace('content="index,follow"', 'content="noindex,follow"')
    open(os.path.join(ROOT, 'deadline.html'), 'w', encoding='utf8').write(html_)
    return {'path': 'deadline.html', 'url': url, 'indexable': indexable, 'count': len(wk), 'changefreq': 'daily', 'priority': '0.9', 'lastmod': TODAY.isoformat(), 'hash': list_hash(wk, nx, soon)}


# ── 월별 ────────────────────────────────────────────────────────


def extra_months(key, allr, months):
    """key(월 페이지)에 붙일, 별도 페이지가 없는 달 목록. 각 달은 그 앞의 가장 가까운 월 페이지(없으면 첫 월 페이지)에 붙는다."""
    if not months: return []
    allk = sorted({k for r in allr.values() for k in months_of(r)} - set(months))
    out = []
    for xk in allk:
        before = [m for m in months if m < xk]
        host = before[-1] if before else months[0]
        if host == key: out.append(xk)
    return out


def build_month(key, allr, fetched, months, regions):
    y, m = int(key[:4]), int(key[5:])
    L = sorted([r for r in allr.values() if month_overlap(r, key)], key=lambda r: (r['start'], r['name']))
    n = len(L)
    live = [r for r in L if r['st']['key'] != 'ended']
    openn = [r for r in L if r['st']['key'] in ('open', 'urgent')]
    soonn = [r for r in L if r['st']['key'] == 'soon']
    infon = [r for r in L if r['st']['key'] == 'info']
    ended = [r for r in L if r['st']['key'] == 'ended']
    byd = collections.Counter(r['date'] for r in L)
    top = byd.most_common(5)
    dist = collections.Counter(t for r in L for t in r['distTags'])
    reg = collections.Counter(r['region'] for r in L if r['region'])
    url = f'{SITE}/month/{key}.html'
    title = (f'{m}월 마라톤 대회 일정 {y} — 전국 {n}개 · 접수 중 {len(openn)}곳 | Run우리' if openn else f'{m}월 마라톤 대회 일정 {y} — 전국 {n}개 대회 총정리 | Run우리')   # SEO P1: \'12월 마라톤\' 을 앞으로
    pk = top[0]; pkd = brp.pd(pk[0])
    d = f'{y}년 {m}월 전국 마라톤·러닝 대회 {n}개. {kd(pkd)}에 {pk[1]}개가 몰려요. 접수 중인 대회와 마감일, 지역·종목별 현황을 정리했어요.'
    if len(d) > 155: d = d[:152].rstrip(' ·,.') + '…'
    dtxt = ' · '.join(f'{k} {dist[k]}개' for k in ('풀', '하프', '10K', '5K') if dist.get(k))
    rtxt = ', '.join(f'{g} {c}개' for g, c in reg.most_common(3))
    lede = (f'{y}년 {m}월에 열리는 대회는 <b>{n}개</b>예요. 지금 접수 중인 대회가 {len(openn)}개, 접수가 아직 열리지 않았거나 일정이 공개되지 않은 대회가 {len(soonn) + len(infon)}개'
            + (f', 이미 끝난 대회가 {len(ended)}개' if ended else '') + '입니다. '
            + (f'종목은 {dtxt}(한 대회에 여러 종목이 있으면 각각 셈)이고, ' if dtxt else '') + (f'지역은 {rtxt} 순으로 많아요.' if rtxt else ''))
    secs = []; no = 1
    note = para(esc((weekday_sentence(L) + ' 출발 시각, 짐 보관, 교통, 기상 악화 시 일정 변경 같은 조건은 대회마다 달라요. 신청 전에 각 대회 공식 안내에서 확인하세요.').strip())) + para(f'접수 중인 대회만 보려면 <a class="ed-link" href="deadline.html">마감 임박 대회</a> 페이지를, 지역을 좁히려면 아래 지역별 모아보기를 이용하세요.')
    secs.append(section(no, f'{m}월 대회, 이렇게 보세요', note, major=True)); no += 1
    trs = ''.join(f'<tr><td>{ks(dt)}</td><td>{c}개</td><td>{esc(", ".join(g for g, _ in collections.Counter(r["region"] for r in L if r["date"] == dt and r["region"]).most_common(3)))}</td></tr>' for dt, c in sorted(top, key=lambda x: x[0]))
    secs.append(section(no, '대회가 몰리는 날', para('같은 날 대회가 많이 겹치는 날이에요. 가고 싶은 대회가 겹치면 접수 마감이 더 빠른 쪽부터 신청하세요.') +
                        f'<table class="ed-table"><thead><tr><th scope="col">날짜</th><th scope="col">대회 수</th><th scope="col">주요 지역</th></tr></thead><tbody>{trs}</tbody></table>')); no += 1
    # 주차별
    buckets = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 31)]
    inner = ''
    last = (datetime.date(y + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1)).day
    for a, b in buckets:
        if a > last: continue   # 2월(28·29일)은 29~31 구간이 없다
        grp = [r for r in L if week_overlap(r, y, m, a, b, last)]
        if not grp: continue
        inner += f'<h3 class="lp-h3">{m}/{a} ~ {m}/{min(b, last)} <span class="ed-small">· {len(grp)}개</span></h3><div class="ed-list" style="border-top:0">{rows(grp)}</div>'
    secs.append(section(no, f'{m}월 전체 대회 (날짜 순)', inner)); no += 1
    other = ''.join(f'<a href="month/{k}.html">{int(k[:4])}년 {int(k[5:])}월</a>' for k in months if k != key)
    reglinks = ''.join(f'<a href="region/{REGIONS[g]}.html">{g}</a>' for g in regions)
    # 대회가 MIN_MONTH 개 미만이라 따로 페이지가 없는 달은 가장 가까운 앞쪽 월 페이지에 붙인다(고아 대회 페이지 방지)
    for xk in extra_months(key, allr, months):
        xl = sorted([r for r in allr.values() if month_overlap(r, xk) and not any(k in months for k in months_of(r))], key=lambda r: (r['start'], r['name']))
        if xl: secs.append(section(no, f'{int(xk[:4])}년 {int(xk[5:])}월 대회 ({len(xl)}개)', para('아직 대회가 적어서 이 달은 따로 모아보기 페이지를 만들지 않았어요. 대회가 늘면 월별 페이지가 생겨요.') + f'<div class="ed-list" style="border-top:0">{rows(xl)}</div>')); no += 1
    secs.append(section(no, '다른 달·지역 모아보기', f'<div class="lp-pills">{other}<a href="deadline.html">마감 임박</a>{reglinks}</div>')); no += 1
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html([("대회 달력", "/")] + ([(f"{y} 마라톤 일정", f"marathon-schedule/{y}.html")] if str(y) in NAVX['years'] else []) + [(f"{y}년 {m}월 대회", f"month/{key}.html")])}'
            f'<div class="landing-title"><h1 class="ed-h1">{y}년 {m}월 마라톤·러닝 대회 일정</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{n}</b>개 · 날짜 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "m" + key)}{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for(f'{y}년 {m}월 마라톤·러닝 대회 일정', url, [('대회 달력', SITE + '/')] + ([(f'{y} 마라톤 일정', f'{SITE}/marathon-schedule/{y}.html')] if str(y) in NAVX['years'] else []) + [(f'{y}년 {m}월 대회', url)], L)
    os.makedirs(os.path.join(ROOT, 'month'), exist_ok=True)
    open(os.path.join(ROOT, 'month', key + '.html'), 'w', encoding='utf8').write(head(title, d, url, ld) + body + tail())
    cf = 'daily' if live else 'yearly'
    return {'path': f'month/{key}.html', 'url': url, 'indexable': True, 'count': n, 'changefreq': cf, 'priority': '0.8' if live else '0.4', 'lastmod': TODAY.isoformat(), 'hash': list_hash(L)}


# ── 지역별 ──────────────────────────────────────────────────────


def build_region(g, cur, fetched, months, regions):
    L = sorted([r for r in cur.values() if r['region'] == g and r['st']['key'] != 'ended'], key=lambda r: (r['date'], r['name']))
    n = len(L)
    running = [r for r in L if r['st']['key'] == 'ongoing']
    openn = [r for r in L if r['st']['key'] in ('open', 'urgent')]
    rest = [r for r in L if r['st']['key'] not in ('open', 'urgent', 'ongoing')]
    bm = collections.Counter(r['date'][:7] for r in L)
    dist = collections.Counter(t for r in L for t in r['distTags'])
    vn = collections.Counter(re.sub(r'\s+', ' ', r['venue']).strip() for r in L if r['venue'])
    venues = [v for v, c in vn.most_common(5) if c >= 2]
    url = f'{SITE}/region/{REGIONS[g]}.html'
    title = f'{g} 마라톤 대회 일정 {years_label(L)} — {n}개 · 접수 중 {len(openn)}곳 | Run우리'   # SEO P1
    d = f'{g}에서 열리는 마라톤·러닝 대회 {n}개. 지금 접수 중인 {len(openn)}개와 월별 일정, 접수 마감일을 공식 정보 기준으로 정리했어요.'
    peak = bm.most_common(1)[0]
    dtxt = ' · '.join(f'{k} {dist[k]}개' for k in ('풀', '하프', '10K', '5K') if dist.get(k))
    lede = (f'{g}에서 앞으로 열리는 대회는 <b>{n}개</b>이고, 이 가운데 지금 접수 중인 대회는 {len(openn)}개예요. '
            f'대회가 가장 많은 달은 {int(peak[0][:4])}년 {int(peak[0][5:])}월({peak[1]}개)입니다.' + (f' 종목은 {dtxt}예요.' if dtxt else ''))
    secs = []; no = 1
    note = para(esc((weekday_sentence(L) + ' 출발지까지 가는 방법(대중교통·셔틀·주차)과 짐 보관 같은 조건은 대회마다 달라요. 신청 전에 각 대회 공식 안내에서 확인하세요.').strip()))
    if venues: note += para('수집된 대회 중 출발지로 자주 나오는 곳은 ' + esc(', '.join(venues)) + '이에요.')
    secs.append(section(no, f'{g} 대회, 이렇게 고르세요', note, major=True)); no += 1
    trs = ''.join(f'<tr><td><a class="ed-link" href="month/{k}.html">{int(k[:4])}년 {int(k[5:])}월</a></td><td>{bm[k]}개</td></tr>' if k in months else f'<tr><td>{int(k[:4])}년 {int(k[5:])}월</td><td>{bm[k]}개</td></tr>' for k in sorted(bm))
    secs.append(section(no, '월별 대회 수', f'<table class="ed-table"><thead><tr><th scope="col">월</th><th scope="col">대회 수</th></tr></thead><tbody>{trs}</tbody></table>')); no += 1
    if running: secs.append(section(no, '지금 진행 중인 대회', f'<div class="ed-list" style="border-top:0">{rows(running)}</div>')); no += 1
    if openn: secs.append(section(no, '지금 접수 중인 대회', f'<div class="ed-list" style="border-top:0">{rows(openn)}</div>')); no += 1
    if rest: secs.append(section(no, '접수 예정·일정 미공지·마감된 대회', f'<div class="ed-list" style="border-top:0">{rows(rest)}</div>')); no += 1
    others = ''.join(f'<a href="region/{REGIONS[x]}.html">{x}</a>' for x in regions if x != g)
    ml = ''.join(f'<a href="month/{k}.html">{int(k[:4])}년 {int(k[5:])}월</a>' for k in months)
    secs.append(section(no, '다른 지역·월 모아보기', f'<div class="lp-pills">{others}{ml}<a href="deadline.html">마감 임박</a></div>')); no += 1
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html([("대회 달력", "/"), (f"{g} 대회", f"region/{REGIONS[g]}.html")])}'
            f'<div class="landing-title"><h1 class="ed-h1">{g} 마라톤·러닝 대회 일정</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{n}</b>개 · 날짜 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "r" + g)}{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for(f'{g} 마라톤·러닝 대회 일정', url, [('대회 달력', SITE + '/'), (f'{g} 대회', url)], L)
    os.makedirs(os.path.join(ROOT, 'region'), exist_ok=True)
    open(os.path.join(ROOT, 'region', REGIONS[g] + '.html'), 'w', encoding='utf8').write(head(title, d, url, ld) + body + tail())
    return {'path': f'region/{REGIONS[g]}.html', 'url': url, 'indexable': True, 'count': n, 'changefreq': 'daily', 'priority': '0.7', 'lastmod': TODAY.isoformat(), 'hash': list_hash(L)}


# ── SEO P1 (2026-11-22): 연도·거리·접수 중 허브 ─────────────────────────
def years_label(L):
    ys = sorted({r['start'][:4] for r in L})
    return '·'.join(ys)


def opt_td(v):
    """값이 없으면 '-' 칸(좁은 화면 카드에서는 숨김)."""
    return f'<td>{esc(v)}</td>' if v else '<td class="lp-empty">-</td>'


def sched_table(lst):
    """날짜·대회·지역·종목·접수 상태 표(정적). 값은 races.json 그대로."""
    trs = ''.join(
        f'<tr><td>{ks(r["start"])}{"~" + ks(r["end"]) if r["end"] != r["start"] else ""}</td><td><a class="ed-link" href="race/{r["id"]}.html">{esc(r["name"])}</a></td>'
        f'{opt_td(r["region"])}{opt_td(" · ".join(r["distTags"]))}<td><span class="ed-status {r["st"]["key"]}">{r["st"]["label"]}</span></td></tr>' for r in lst)
    return (f'<div class="lp-tablewrap"><table class="ed-table lp-sched"><thead><tr><th scope="col">날짜</th><th scope="col">대회</th><th scope="col">지역</th><th scope="col">종목</th><th scope="col">접수</th></tr></thead>'
            f'<tbody>{trs}</tbody></table></div>')


def other_hubs(here):
    """연도·거리·접수 중 허브 알약 링크(자기 자신 제외)."""
    out = ''.join(f'<a href="marathon-schedule/{y}.html">{y} 마라톤 일정</a>' for y in NAVX['years'] if 'y' + y != here)
    out += ''.join(f'<a href="distance/{s}.html">{lab} 대회</a>' for s, lab in NAVX['dists'] if 'd' + s != here)
    if NAVX['open'] and here != 'open': out += '<a href="open.html">접수 중인 대회</a>'
    return out


def build_year(y, allr, cur, fetched, months, regions):
    L = sorted([r for r in allr.values() if r['start'][:4] == y], key=lambda r: (r['start'], r['name']))
    n = len(L)
    ended = [r for r in L if r['st']['key'] == 'ended']; live = [r for r in L if r['st']['key'] != 'ended']
    openn = [r for r in L if r['st']['key'] in ('open', 'urgent')]
    bm = collections.Counter(r['start'][:7] for r in L)
    mk = sorted(bm)
    dist = collections.Counter(t for r in L for t in r['distTags'])
    reg = collections.Counter(r['region'] for r in L if r['region'])
    url = f'{SITE}/marathon-schedule/{y}.html'
    span = f'{int(mk[0][5:])}~{int(mk[-1][5:])}월' if len(mk) > 1 else f'{int(mk[0][5:])}월'
    if ended and not live:
        title = f'{y} 마라톤 대회 일정 총정리 — {span} 전국 {n}개 대회 | Run우리'
    elif ended:
        title = f'{y} 마라톤 대회 일정 총정리 — 전국 {n}개 · 남은 대회 {len(live)}개 | Run우리'
    else:
        title = f'{y} 마라톤 대회 일정 — 월별 전국 대회 {n}개 · 접수 중 {len(openn)}곳 | Run우리'
    d = (f'{y}년 전국 마라톤·러닝 대회 {n}개를 월별로 정리했어요({span}). ' + (f'남은 대회 {len(live)}개는 접수 상태까지, ' if live else '')
         + ('끝난 대회는 일정과 종목 기록용으로 남겨 뒀어요.' if ended else '종목·지역·접수 기간을 공식 정보 기준으로 확인하세요.'))
    if len(d) > 155: d = d[:152].rstrip(' ·,.') + '…'
    dtxt = ' · '.join(f'{k} {dist[k]}개' for k in ('풀', '하프', '10K', '5K') if dist.get(k))
    rtxt = ', '.join(f'{g} {c}개' for g, c in reg.most_common(3))
    pk = bm.most_common(1)[0]
    lede = (f'Run우리 대회 달력에 담긴 {y}년 대회는 <b>{n}개</b>예요({span}). '
            + (f'이미 끝난 대회가 {len(ended)}개, 앞으로 열리는 대회가 {len(live)}개이고, 지금 접수 중인 대회는 {len(openn)}개예요. ' if ended else f'지금 접수 중인 대회는 {len(openn)}개예요. ')
            + f'대회가 가장 많은 달은 {int(pk[0][5:])}월({pk[1]}개)이에요. ' + (f'종목은 {dtxt}(한 대회에 여러 종목이 있으면 각각 셈)이고, ' if dtxt else '')
            + (f'지역은 {rtxt} 순으로 많아요.' if rtxt else ''))
    secs = []; no = 1
    trs = ''.join(f'<tr><td>' + (f'<a class="ed-link" href="month/{k}.html">{int(k[5:])}월</a>' if k in months else f'{int(k[5:])}월') + f'</td><td>{bm[k]}개</td>'
                  f'<td>{sum(1 for r in L if r["start"][:7] == k and r["st"]["key"] in ("open", "urgent"))}개</td></tr>' for k in mk)
    secs.append(section(no, f'{y}년 월별 대회 수', para('월 이름을 누르면 그달 대회를 주차별로 볼 수 있어요. 별도 페이지가 없는 달은 아래 표에서 바로 확인하세요.')
                        + f'<table class="ed-table"><thead><tr><th scope="col">월</th><th scope="col">대회 수</th><th scope="col">지금 접수 중</th></tr></thead><tbody>{trs}</tbody></table>', major=True)); no += 1
    for k in mk:
        lst = [r for r in L if r['start'][:7] == k]
        secs.append(section(no, f'{y}년 {int(k[5:])}월 ({len(lst)}개)', sched_table(lst), more=(f'month/{k}.html', f'{int(k[5:])}월 자세히') if k in months else None)); no += 1
    secs.append(section(no, '다른 모아보기', f'<div class="lp-pills">{other_hubs("y" + y)}<a href="deadline.html">마감 임박</a></div>')); no += 1
    trail = [("대회 달력", "/"), (f"{y} 마라톤 일정", f"marathon-schedule/{y}.html")]
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html(trail)}'
            f'<div class="landing-title"><h1 class="ed-h1">{y} 마라톤 대회 일정</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{n}</b>개 · 월별</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "y" + y)}{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for(f'{y} 마라톤 대회 일정', url, [('대회 달력', SITE + '/'), (f'{y} 마라톤 일정', url)], L)
    os.makedirs(os.path.join(ROOT, 'marathon-schedule'), exist_ok=True)
    open(os.path.join(ROOT, 'marathon-schedule', y + '.html'), 'w', encoding='utf8').write(head(title, d, url, ld) + body + tail())
    return {'path': f'marathon-schedule/{y}.html', 'url': url, 'indexable': True, 'count': n, 'changefreq': 'daily' if live else 'monthly', 'priority': '0.8', 'lastmod': TODAY.isoformat(), 'hash': list_hash(L)}


DIST_GUIDES = {'하프': [('half-marathon-prep', '하프 마라톤 준비하기'), ('race-pace-strategy', '대회 페이스 전략')],
               '10K': [('10k-training-plan', '10km 러닝 플랜'), ('race-pace-strategy', '대회 페이스 전략')],
               '5K': [('beginner-5k-plan', '초보자 5km 완주 훈련 계획'), ('understanding-pace', '페이스 이해하기')],
               '풀': [('first-marathon-checklist', '첫 마라톤 체크리스트'), ('marathon-prep-and-taper', '마라톤 준비와 테이퍼')]}


def _guide_title(gid, fallback):
    try:
        for p in json.load(open(os.path.join(ROOT, 'data', 'blog', 'index.json'), encoding='utf8'))['posts']:
            if p['id'] == gid: return p['title'].split(':')[0].strip()
    except Exception: pass
    return fallback


def dist_fee(lst, tag):
    """그 거리 종목(수집기 tag_of 기준)의 참가비만 모아 범위를 낸다. 참가비 미확인 종목은 빼고 센다."""
    fees, n_races = [], 0
    for r in lst:
        f = [d['fee'] for d in r['distances'] if d.get('fee') is not None and d.get('km') is not None and brp._norm and brp._norm.tag_of(d['km']) == tag]
        if f: fees += f; n_races += 1
    return fees, n_races


def won(n): return '무료' if n == 0 else f'{n:,}원'


def build_dist(slug, tag, label, km, cur, fetched, months, regions, indexable):
    L = sorted([r for r in cur.values() if r['st']['key'] != 'ended' and tag in r['distTags']], key=lambda r: (r['start'], r['name']))
    n = len(L)
    openn = sorted([r for r in L if r['st']['key'] in ('open', 'urgent')], key=lambda r: (r['close'] or '9999', r['start']))
    bm = collections.Counter(r['start'][:7] for r in L)
    reg = collections.Counter(r['region'] for r in L if r['region'])
    fees, nf = dist_fee(L, tag)
    url = f'{SITE}/distance/{slug}.html'
    yl = years_label(L) or str(TODAY.year)
    title = f'{label} 대회 일정 {yl} — 다가오는 {n}개 · 접수 중 {len(openn)}곳 | Run우리'
    d = f'{km} {label.replace(" 마라톤", "")} 종목이 있는 전국 대회 {n}개. 월별·지역별로 정리하고 참가비 범위와 접수 마감일을 함께 보여드려요.'
    if len(d) > 155: d = d[:152].rstrip(' ·,.') + '…'
    rtxt = ', '.join(f'{g} {c}개' for g, c in reg.most_common(3))
    pk = bm.most_common(1)[0] if bm else None
    lede = (f'{TODAY.month}월 {TODAY.day}일 기준으로 {km} {label.replace(" 마라톤", "")} 종목이 있는 다가오는 대회는 <b>{n}개</b>이고, 지금 접수 중인 대회는 {len(openn)}개예요. '
            + (f'대회가 가장 많은 달은 {int(pk[0][:4])}년 {int(pk[0][5:])}월({pk[1]}개)이고, ' if pk else '') + (f'지역은 {rtxt} 순으로 많아요. ' if rtxt else '')
            + (f'참가비가 확인된 {nf}개 대회의 이 종목 참가비는 {won(min(fees))}~{won(max(fees))}예요.' if fees else '이 종목 참가비는 아직 확인된 값이 없어요.'))
    secs = []; no = 1
    gl = ''.join(f'<li><a class="ed-link" href="guide/{g}.html">{esc(_guide_title(g, t))}</a></li>' for g, t in DIST_GUIDES.get(tag, []) if os.path.exists(os.path.join(ROOT, 'guide', g + '.html')))
    note = para(f'종목 구분은 대회가 공지한 거리로 나눠요. 같은 대회에 다른 거리 종목이 함께 있을 수 있고, 제한 시간·참가 자격·기념품 조건은 대회마다 달라요. 신청 전에 각 대회 공식 안내를 확인하세요.')
    note += f'<ul class="ed-small" style="line-height:2;margin:10px 0 0 18px;padding:0"><li><a class="ed-link" href="tools/pace-calculator.html">{km} 목표 기록 페이스 계산하기</a></li>{gl}</ul>'
    secs.append(section(no, f'{label} 대회, 이렇게 보세요', note, major=True)); no += 1
    if openn: secs.append(section(no, f'지금 접수 중 ({len(openn)}개, 마감일 순)', f'<div class="ed-list" style="border-top:0">{rows(openn)}</div>')); no += 1
    trs = ''.join(f'<tr><td>' + (f'<a class="ed-link" href="month/{k}.html">{int(k[:4])}년 {int(k[5:])}월</a>' if k in months else f'{int(k[:4])}년 {int(k[5:])}월') + f'</td><td>{bm[k]}개</td></tr>' for k in sorted(bm))
    secs.append(section(no, '월별 대회 수', f'<table class="ed-table"><thead><tr><th scope="col">월</th><th scope="col">대회 수</th></tr></thead><tbody>{trs}</tbody></table>')); no += 1
    secs.append(section(no, f'{label} 대회 전체 (날짜 순)', sched_table(L))); no += 1
    secs.append(section(no, '다른 모아보기', f'<div class="lp-pills">{other_hubs("d" + slug)}<a href="deadline.html">마감 임박</a></div>')); no += 1
    trail = [("대회 달력", "/"), (f"{label} 대회", f"distance/{slug}.html")]
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html(trail)}'
            f'<div class="landing-title"><h1 class="ed-h1">{label} 대회 일정</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{n}</b>개 · 날짜 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "d" + slug)}{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for(f'{label} 대회 일정', url, [('대회 달력', SITE + '/'), (f'{label} 대회', url)], L)
    html_ = head(title, d, url, ld) + body + tail()
    if not indexable: html_ = html_.replace('content="index,follow"', 'content="noindex,follow"')
    os.makedirs(os.path.join(ROOT, 'distance'), exist_ok=True)
    open(os.path.join(ROOT, 'distance', slug + '.html'), 'w', encoding='utf8').write(html_)
    return {'path': f'distance/{slug}.html', 'url': url, 'indexable': indexable, 'count': n, 'changefreq': 'daily', 'priority': '0.8', 'lastmod': TODAY.isoformat(), 'hash': list_hash(L)}


def build_open(cur, fetched, months, regions):
    L = sorted([r for r in cur.values() if r['st']['key'] in ('open', 'urgent')], key=lambda r: (r['close'] or '9999', r['start']))
    soon = sorted([r for r in cur.values() if r['st']['key'] == 'soon'], key=lambda r: (r['open'] or '9999', r['start']))
    n = len(L); indexable = n >= MIN_HUB
    url = f'{SITE}/open.html'
    title = f'지금 접수 중인 마라톤 대회 {n}곳 — 마감일순 정리 | Run우리'
    d = f'오늘({TODAY.month}/{TODAY.day}) 접수할 수 있는 전국 마라톤·러닝 대회 {n}곳을 마감일 순으로 모았어요.' + (f' 곧 접수가 열리는 대회 {len(soon)}곳도 함께.' if soon else '')
    urg = [r for r in L if r['st']['key'] == 'urgent']
    noclose = [r for r in L if not r['close']]
    dist = collections.Counter(t for r in L for t in r['distTags'])
    dtxt = ' · '.join(f'{k} {dist[k]}개' for k in ('풀', '하프', '10K', '5K') if dist.get(k))
    lede = (f'{TODAY.month}월 {TODAY.day}일({WDK[TODAY.weekday()]}) 기준으로 접수할 수 있는 대회는 <b>{n}개</b>예요. 그중 {len(urg)}개는 접수 마감이 10일 안으로 다가왔고'
            + (f', {len(noclose)}개는 마감일이 공지되지 않았거나 정원이 차면 마감돼요' if noclose else '') + '. '
            + (f'종목은 {dtxt}(한 대회에 여러 종목이 있으면 각각 셈)예요. ' if dtxt else '') + '목록은 접수 마감일이 빠른 순서예요.')
    secs = []; no = 1
    secs.append(section(no, f'접수 중인 대회 ({n}개, 마감일 순)', f'<div class="ed-list" style="border-top:0">{rows(L)}</div>' if L else para('지금 접수 중인 대회가 없어요.'), major=True)); no += 1
    if soon: secs.append(section(no, f'곧 접수가 열리는 대회 ({len(soon)}개)', para('접수 시작일과 시각은 공식 홈페이지 공지를 확인하세요.') + f'<div class="ed-list" style="border-top:0">{rows(soon)}</div>')); no += 1
    secs.append(section(no, '다른 모아보기', f'<div class="lp-pills">{other_hubs("open")}<a href="deadline.html">이번 주 마감</a></div>')); no += 1
    trail = [("대회 달력", "/"), ("접수 중인 대회", "open.html")]
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html(trail)}'
            f'<div class="landing-title"><h1 class="ed-h1">지금 접수 중인 마라톤 대회</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{n}</b>개 · 마감일 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "open")}{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for('지금 접수 중인 마라톤 대회', url, [('대회 달력', SITE + '/'), ('접수 중인 대회', url)], L)
    html_ = head(title, d, url, ld) + body + tail()
    if not indexable: html_ = html_.replace('content="index,follow"', 'content="noindex,follow"')
    open(os.path.join(ROOT, 'open.html'), 'w', encoding='utf8').write(html_)
    return {'path': 'open.html', 'url': url, 'indexable': indexable, 'count': n, 'changefreq': 'daily', 'priority': '0.9', 'lastmod': TODAY.isoformat(), 'hash': list_hash(L, soon)}


def inject_index(months, regions):
    """홈(index.html)의 제목 아래에 정적 링크 블록을 넣는다(크롤러·이용자 모두 바로 보이게)."""
    p = os.path.join(ROOT, 'index.html'); s = open(p, encoding='utf8').read()
    block = ('<!--LANDING:START-->' + nav_block(months, regions, '').replace('class="lp-links"', 'class="lp-links lp-home"').replace('aria-label="대회 모아보기"', 'aria-label="접수·연도·월별·지역·거리별 모아보기"') + '<!--LANDING:END-->')
    s = re.sub(r'\n?<!--LANDING:START-->.*?<!--LANDING:END-->', '', s, flags=re.S)
    assert '<div class="split">' in s
    s = s.replace('<div class="split">', block + '\n<div class="split">', 1)
    open(p, 'w', encoding='utf8').write(s)


def main():
    cur, allr, fetched = read_races()
    months = month_keys(allr); regions = region_keys(cur)
    NAVX['years'] = year_keys(allr)
    di = dist_indexable(cur)
    NAVX['dists'] = [(sl, lab) for sl, t, lab, _ in DISTS if t in di]
    NAVX['open'] = sum(1 for r in cur.values() if r['st']['key'] in ('open', 'urgent')) >= MIN_HUB
    for sub in ('month', 'region', 'marathon-schedule', 'distance'):
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)
        for f in os.listdir(os.path.join(ROOT, sub)):
            if f.endswith('.html'): os.remove(os.path.join(ROOT, sub, f))
    out = [build_deadline(cur, fetched, months, regions)]
    out += [build_month(k, allr, fetched, months, regions) for k in months]
    out += [build_region(g, cur, fetched, months, regions) for g in regions]
    out += [build_year(y, allr, cur, fetched, months, regions) for y in NAVX['years']]
    out += [build_dist(sl, t, lab, km, cur, fetched, months, regions, t in di) for sl, t, lab, km in DISTS if any(t in r['distTags'] for r in cur.values() if r['st']['key'] != 'ended')]
    out.append(build_open(cur, fetched, months, regions))
    inject_index(months, regions)
    json.dump({'generated': TODAY.isoformat(), 'pages': out}, open(os.path.join(ROOT, 'data', 'landing_pages.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    print('landing pages:', len(out), [(p['path'], p['count'], 'idx' if p['indexable'] else 'noindex') for p in out])


if __name__ == '__main__': main()
