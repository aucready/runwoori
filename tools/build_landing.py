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
import json, os, re, sys, html, datetime, collections
sys.path.insert(0, os.path.dirname(__file__))
import build_race_pages as brp
import build_overseas as bo

ROOT = brp.ROOT; SITE = brp.SITE; TODAY = brp.TODAY
MIN_MONTH = 15        # 월별 페이지: 색인 허용 대회 수 최소
MIN_REGION = 15       # 지역별 페이지: 예정 대회 수 최소
MIN_DEADLINE = 5      # 마감 임박 페이지: 목록(7일 내 + 이어지는 마감) 최소
esc = brp.esc
SEP = brp.SEP
WDK = ['월', '화', '수', '목', '금', '토', '일']   # date.weekday() 기준


def kd(d): return f'{d.month}/{d.day}({WDK[d.weekday()]})'
def ks(s): d = brp.pd(s); return f'{d.month}/{d.day}({WDK[d.weekday()]})'

REGIONS = {'서울': 'seoul', '경기': 'gyeonggi', '인천': 'incheon', '강원': 'gangwon', '충북': 'chungbuk', '충남': 'chungnam', '대전': 'daejeon', '세종': 'sejong',
           '전북': 'jeonbuk', '전남': 'jeonnam', '광주': 'gwangju', '경북': 'gyeongbuk', '경남': 'gyeongnam', '대구': 'daegu', '울산': 'ulsan', '부산': 'busan', '제주': 'jeju'}

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


def nav_block(months, regions, here):
    a = lambda href, label, key: f'<a href="{href}"{" aria-current=\"page\" class=\"is-on\"" if key == here else ""}>{esc(label)}</a>'
    ml = ''.join(a(f'month/{m}.html', f'{int(m[5:])}월', 'm' + m) for m in months)
    rl = ''.join(a(f'region/{REGIONS[g]}.html', g, 'r' + g) for g in regions)
    out = f'<div class="lp-links-row"><span class="ed-label">마감</span>{a("deadline.html", "마감 임박", "deadline")}</div>'
    if ml: out += f'<div class="lp-links-row"><span class="ed-label">월별</span>{ml}</div>'
    if rl: out += f'<div class="lp-links-row"><span class="ed-label">지역별</span>{rl}</div>'
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
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html([("대회 달력", "index.html"), ("마감 임박 대회", "deadline.html")])}'
            f'<div class="landing-title"><h1 class="ed-h1">이번 주 접수 마감 대회</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{len(wk)}</b>개 · 마감일 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "deadline")}'
            f'{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for('이번 주 접수 마감 대회', url, [('대회 달력', SITE + '/'), ('마감 임박 대회', url)], wk + nx)
    html_ = head(title, d, url, ld) + body + tail()
    if not indexable: html_ = html_.replace('content="index,follow"', 'content="noindex,follow"')
    open(os.path.join(ROOT, 'deadline.html'), 'w', encoding='utf8').write(html_)
    return {'path': 'deadline.html', 'url': url, 'indexable': indexable, 'count': len(wk), 'changefreq': 'daily', 'priority': '0.9', 'lastmod': TODAY.isoformat()}


# ── 월별 ────────────────────────────────────────────────────────
def month_keys(allr):
    c = collections.Counter(r['date'][:7] for r in allr.values())
    return sorted(k for k, v in c.items() if v >= MIN_MONTH)


def build_month(key, allr, fetched, months, regions):
    y, m = int(key[:4]), int(key[5:])
    L = sorted([r for r in allr.values() if r['date'][:7] == key], key=lambda r: (r['date'], r['name']))
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
    title = f'{y}년 {m}월 마라톤·러닝 대회 일정 총정리 ({n}개) | Run우리'
    pk = top[0]; pkd = brp.pd(pk[0])
    d = f'{y}년 {m}월 전국 마라톤·러닝 대회 {n}개. {kd(pkd)}에 {pk[1]}개가 몰려요. 접수 중인 대회와 마감일, 지역·종목별 현황을 정리했어요.'
    if len(d) > 155: d = d[:152].rstrip(' ·,.') + '…'
    dtxt = ' · '.join(f'{k} {dist[k]}개' for k in ('풀', '하프', '10K', '5K') if dist.get(k))
    rtxt = ', '.join(f'{g} {c}개' for g, c in reg.most_common(3))
    lede = (f'{y}년 {m}월에 열리는 대회는 <b>{n}개</b>예요. 지금 접수 중인 대회가 {len(openn)}개, 접수가 아직 열리지 않았거나 일정이 공개되지 않은 대회가 {len(soonn) + len(infon)}개'
            + (f', 이미 끝난 대회가 {len(ended)}개' if ended else '') + '입니다. '
            + (f'종목은 {dtxt}(한 대회에 여러 종목이 있으면 각각 셈)이고, ' if dtxt else '') + (f'지역은 {rtxt} 순으로 많아요.' if rtxt else ''))
    secs = []; no = 1
    note = para(esc(weekday_sentence(L) + ' 출발 시각, 짐 보관, 교통, 기상 악화 시 일정 변경 같은 조건은 대회마다 달라요. 신청 전에 각 대회 공식 안내에서 확인하세요.')) + para(f'접수 중인 대회만 보려면 <a class="ed-link" href="deadline.html">마감 임박 대회</a> 페이지를, 지역을 좁히려면 아래 지역별 모아보기를 이용하세요.')
    secs.append(section(no, f'{m}월 대회, 이렇게 보세요', note, major=True)); no += 1
    trs = ''.join(f'<tr><td>{ks(dt)}</td><td>{c}개</td><td>{esc(", ".join(g for g, _ in collections.Counter(r["region"] for r in L if r["date"] == dt and r["region"]).most_common(3)))}</td></tr>' for dt, c in sorted(top, key=lambda x: x[0]))
    secs.append(section(no, '대회가 몰리는 날', para('같은 날 대회가 많이 겹치는 날이에요. 가고 싶은 대회가 겹치면 접수 마감이 더 빠른 쪽부터 신청하세요.') +
                        f'<table class="ed-table"><thead><tr><th scope="col">날짜</th><th scope="col">대회 수</th><th scope="col">주요 지역</th></tr></thead><tbody>{trs}</tbody></table>')); no += 1
    # 주차별
    buckets = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 31)]
    inner = ''
    last = (datetime.date(y + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1)).day
    for a, b in buckets:
        grp = [r for r in L if a <= brp.pd(r['date']).day <= b]
        if not grp: continue
        inner += f'<h3 class="lp-h3">{m}/{a} ~ {m}/{min(b, last)} <span class="ed-small">· {len(grp)}개</span></h3><div class="ed-list" style="border-top:0">{rows(grp)}</div>'
    secs.append(section(no, f'{m}월 전체 대회 (날짜 순)', inner)); no += 1
    other = ''.join(f'<a href="month/{k}.html">{int(k[:4])}년 {int(k[5:])}월</a>' for k in months if k != key)
    reglinks = ''.join(f'<a href="region/{REGIONS[g]}.html">{g}</a>' for g in regions)
    secs.append(section(no, '다른 달·지역 모아보기', f'<div class="lp-pills">{other}<a href="deadline.html">마감 임박</a>{reglinks}</div>')); no += 1
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html([("대회 달력", "index.html"), (f"{y}년 {m}월 대회", f"month/{key}.html")])}'
            f'<div class="landing-title"><h1 class="ed-h1">{y}년 {m}월 마라톤·러닝 대회 일정</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{n}</b>개 · 날짜 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "m" + key)}{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for(f'{y}년 {m}월 마라톤·러닝 대회 일정', url, [('대회 달력', SITE + '/'), (f'{y}년 {m}월 대회', url)], L)
    os.makedirs(os.path.join(ROOT, 'month'), exist_ok=True)
    open(os.path.join(ROOT, 'month', key + '.html'), 'w', encoding='utf8').write(head(title, d, url, ld) + body + tail())
    cf = 'daily' if live else 'yearly'
    return {'path': f'month/{key}.html', 'url': url, 'indexable': True, 'count': n, 'changefreq': cf, 'priority': '0.8' if live else '0.4', 'lastmod': TODAY.isoformat()}


# ── 지역별 ──────────────────────────────────────────────────────
def region_keys(cur):
    c = collections.Counter(r['region'] for r in cur.values() if r['st']['key'] != 'ended' and r['region'] in REGIONS)
    return [g for g, v in c.most_common() if v >= MIN_REGION]


def build_region(g, cur, fetched, months, regions):
    L = sorted([r for r in cur.values() if r['region'] == g and r['st']['key'] != 'ended'], key=lambda r: (r['date'], r['name']))
    n = len(L)
    openn = [r for r in L if r['st']['key'] in ('open', 'urgent')]
    rest = [r for r in L if r['st']['key'] not in ('open', 'urgent')]
    bm = collections.Counter(r['date'][:7] for r in L)
    dist = collections.Counter(t for r in L for t in r['distTags'])
    vn = collections.Counter(re.sub(r'\s+', ' ', r['venue']).strip() for r in L if r['venue'])
    venues = [v for v, c in vn.most_common(5) if c >= 2]
    url = f'{SITE}/region/{REGIONS[g]}.html'
    title = f'{g} 마라톤·러닝 대회 일정 ({n}개) 접수 현황 | Run우리'
    d = f'{g}에서 열리는 마라톤·러닝 대회 {n}개. 지금 접수 중인 {len(openn)}개와 월별 일정, 접수 마감일을 공식 정보 기준으로 정리했어요.'
    peak = bm.most_common(1)[0]
    dtxt = ' · '.join(f'{k} {dist[k]}개' for k in ('풀', '하프', '10K', '5K') if dist.get(k))
    lede = (f'{g}에서 앞으로 열리는 대회는 <b>{n}개</b>이고, 이 가운데 지금 접수 중인 대회는 {len(openn)}개예요. '
            f'대회가 가장 많은 달은 {int(peak[0][:4])}년 {int(peak[0][5:])}월({peak[1]}개)입니다.' + (f' 종목은 {dtxt}예요.' if dtxt else ''))
    secs = []; no = 1
    note = para(esc(weekday_sentence(L) + ' 출발지까지 가는 방법(대중교통·셔틀·주차)과 짐 보관 같은 조건은 대회마다 달라요. 신청 전에 각 대회 공식 안내에서 확인하세요.'))
    if venues: note += para('수집된 대회 중 출발지로 자주 나오는 곳은 ' + esc(', '.join(venues)) + '이에요.')
    secs.append(section(no, f'{g} 대회, 이렇게 고르세요', note, major=True)); no += 1
    trs = ''.join(f'<tr><td><a class="ed-link" href="month/{k}.html">{int(k[:4])}년 {int(k[5:])}월</a></td><td>{bm[k]}개</td></tr>' if k in months else f'<tr><td>{int(k[:4])}년 {int(k[5:])}월</td><td>{bm[k]}개</td></tr>' for k in sorted(bm))
    secs.append(section(no, '월별 대회 수', f'<table class="ed-table"><thead><tr><th scope="col">월</th><th scope="col">대회 수</th></tr></thead><tbody>{trs}</tbody></table>')); no += 1
    if openn: secs.append(section(no, '지금 접수 중인 대회', f'<div class="ed-list" style="border-top:0">{rows(openn)}</div>')); no += 1
    if rest: secs.append(section(no, '접수 예정·일정 미공지·마감된 대회', f'<div class="ed-list" style="border-top:0">{rows(rest)}</div>')); no += 1
    others = ''.join(f'<a href="region/{REGIONS[x]}.html">{x}</a>' for x in regions if x != g)
    ml = ''.join(f'<a href="month/{k}.html">{int(k[:4])}년 {int(k[5:])}월</a>' for k in months)
    secs.append(section(no, '다른 지역·월 모아보기', f'<div class="lp-pills">{others}{ml}<a href="deadline.html">마감 임박</a></div>')); no += 1
    body = (f'<main class="ed-wrap" id="main"><div id="view">{crumbs_html([("대회 달력", "index.html"), (f"{g} 대회", f"region/{REGIONS[g]}.html")])}'
            f'<div class="landing-title"><h1 class="ed-h1">{g} 마라톤·러닝 대회 일정</h1><p class="ed-small ed-tab-num"><b style="color:var(--ink)">{n}</b>개 · 날짜 순</p></div>'
            f'<p class="ed-lede lp-lede">{lede}</p>{nav_block(months, regions, "r" + g)}{"".join(secs)}<div class="lp-end">{stamp(fetched)}</div></div></main>\n')
    ld = ld_for(f'{g} 마라톤·러닝 대회 일정', url, [('대회 달력', SITE + '/'), (f'{g} 대회', url)], L)
    os.makedirs(os.path.join(ROOT, 'region'), exist_ok=True)
    open(os.path.join(ROOT, 'region', REGIONS[g] + '.html'), 'w', encoding='utf8').write(head(title, d, url, ld) + body + tail())
    return {'path': f'region/{REGIONS[g]}.html', 'url': url, 'indexable': True, 'count': n, 'changefreq': 'daily', 'priority': '0.7', 'lastmod': TODAY.isoformat()}


def inject_index(months, regions):
    """홈(index.html)의 제목 아래에 정적 링크 블록을 넣는다(크롤러·이용자 모두 바로 보이게)."""
    p = os.path.join(ROOT, 'index.html'); s = open(p, encoding='utf8').read()
    block = ('<!--LANDING:START-->' + nav_block(months, regions, '').replace('class="lp-links"', 'class="lp-links lp-home"').replace('aria-label="대회 모아보기"', 'aria-label="마감·월별·지역별 모아보기"') + '<!--LANDING:END-->')
    s = re.sub(r'\n?<!--LANDING:START-->.*?<!--LANDING:END-->', '', s, flags=re.S)
    assert '<div class="split">' in s
    s = s.replace('<div class="split">', block + '\n<div class="split">', 1)
    open(p, 'w', encoding='utf8').write(s)


def main():
    cur, allr, fetched = read_races()
    months = month_keys(allr); regions = region_keys(cur)
    for sub in ('month', 'region'):
        os.makedirs(os.path.join(ROOT, sub), exist_ok=True)
        for f in os.listdir(os.path.join(ROOT, sub)):
            if f.endswith('.html'): os.remove(os.path.join(ROOT, sub, f))
    out = [build_deadline(cur, fetched, months, regions)]
    out += [build_month(k, allr, fetched, months, regions) for k in months]
    out += [build_region(g, cur, fetched, months, regions) for g in regions]
    inject_index(months, regions)
    json.dump({'generated': TODAY.isoformat(), 'pages': out}, open(os.path.join(ROOT, 'data', 'landing_pages.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=0)
    print('landing pages:', len(out), [(p['path'], p['count'], 'idx' if p['indexable'] else 'noindex') for p in out])


if __name__ == '__main__': main()
