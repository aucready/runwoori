#!/usr/bin/env python3
"""메인(index.html) 정적 프리렌더 (SEO P0, 2026-11-22).

  python3 tools/build_home.py      # build_landing.py 다음에 실행(daily_publish.sh)

- data/races.json 으로 app.js 가 처음 그리는 화면(현황 숫자·필터 칩·이번 달 달력·목록 탭·대회 목록)을
  같은 마크업으로 미리 넣는다. 목록은 기본 정렬(접수 중 먼저 → 대회일 가까운 순) 앞쪽 HOME_N 개.
- app.js 는 그대로 innerHTML 을 다시 그리므로 필터·검색·저장 기능은 지금과 같고, 그 전에 같은 내용이 이미 있어서
  화면이 밀리지 않는다(CLS). 구글은 JS 를 돌리지 않아도 대회 목록·링크를 읽는다.
- <!--PRE:키-->…<!--/PRE:키--> 사이만 바꾼다. lede(실제 숫자로 계산한 리드 문장), ld(ItemList JSON-LD)도 같은 방식.
- 데이터 원칙: races.json(KorMarathon 수집 + 공식 홈페이지 보정)만 쓴다. 문장의 숫자는 모두 여기서 계산한다.
"""
import json, os, re, sys, datetime, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_race_pages as brp

ROOT = brp.ROOT; SITE = brp.SITE; TODAY = brp.TODAY; esc = brp.esc
HOME_N = 50
WD = brp.WD   # 일=0
EN = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
RANK = {'ongoing': -1, 'urgent': 0, 'open': 0, 'soon': 1, 'info': 2, 'closed': 3, 'ended': 4}
STAT = [('all', '전체'), ('ongoing', '진행 중'), ('open', '접수중'), ('urgent', '마감임박'), ('soon', '접수예정'), ('info', '일정 미공지'), ('closed', '마감')]
REG_ORDER = ['서울', '경기', '인천', '강원', '충북', '충남', '대전', '세종', '전북', '전남', '광주', '경북', '경남', '대구', '울산', '부산', '제주', '전국']
DIST = [('전체', '전체'), ('5K', '5K'), ('10K', '10K'), ('하프', '하프'), ('풀', '풀코스')]


def jsdow(d): return (d.weekday() + 1) % 7


def chips(items, key, cur, counts=None):
    return ''.join(f'<button class="{"is-on" if v == cur else ""}" data-k="{key}" data-v="{v}">{l}'
                   + (f'<span class="c">{counts[v]}</span>' if counts and counts.get(v) is not None else '') + '</button>' for v, l in items)


def cal_html(live):
    t = TODAY; y, mo = t.year, t.month
    last = calendar.monthrange(y, mo)[1]
    m0, m1 = datetime.date(y, mo, 1), datetime.date(y, mo, last)
    base = [r for r in live if r['start'] <= m1.isoformat() and r['end'] >= m0.isoformat()]
    day_map = {}
    for r in base:
        a = max(brp.pd(r['start']), m0); b = min(brp.pd(r['end']), m1)
        d = a
        while d <= b:
            day_map.setdefault(d.isoformat(), []).append(r); d += datetime.timedelta(days=1)
    first = jsdow(m0)
    prev_last = (m0 - datetime.timedelta(days=1)).day
    pm = (mo - 2) % 12 + 1; nm = mo % 12 + 1
    h = (f'<div class="ed-cal-head"><h2>{y}년 {mo}월</h2><div class="nav"><button id="prev" aria-label="{pm}월로">← {pm}월</button><button id="todayBtn">오늘</button>'
         f'<button id="next" aria-label="{nm}월로">{nm}월 →</button></div></div><div class="ed-cal-grid">')
    h += ''.join(f'<div class="ed-cal-dow">{d}</div>' for d in WD)
    for i in range(first - 1, -1, -1): h += f'<div class="ed-cal-day mute">{prev_last - i}</div>'
    for d in range(1, last + 1):
        dd = datetime.date(y, mo, d); k = dd.isoformat(); dw = jsdow(dd); rs = day_map.get(k, [])
        seen = []
        for r in rs:
            if r['st']['key'] not in seen: seen.append(r['st']['key'])
        dots = ''.join(f'<i class="{s}"></i>' for s in seen[:3]) + (f'<b class="ct">{len(rs)}</b>' if len(rs) > 1 else '')
        nmh = ''.join(f'<span class="nm">{esc(re.sub(r"^20\d\d\s*", "", r["name"]))}</span>' for r in rs[:2]) + (f'<span class="nm more">+{len(rs) - 2}</span>' if len(rs) > 2 else '')
        cls = f'ed-cal-day {"sun" if dw == 0 else ""} {"sat" if dw == 6 else ""} {"has" if rs else ""} {"today" if dd == t else ""} '
        h += (f'<button class="{cls}" data-day="{k}" aria-pressed="false" aria-label="{mo}월 {d}일 대회 {len(rs)}개">{d}<span class="m">{dots}</span><span class="nms">{nmh}</span></button>'
              if rs else f'<div class="{cls}">{d}<span class="m"></span></div>')
    used = first + last; tail = (7 - used % 7) % 7
    h += ''.join(f'<div class="ed-cal-day mute">{i}</div>' for i in range(1, tail + 1))
    h += ('</div><div class="ed-cal-legend"><span class="ed-status ongoing">진행 중</span><span class="ed-status open">접수중</span><span class="ed-status urgent">마감임박</span>'
          '<span class="ed-status soon">접수예정</span><span class="ed-status closed">마감</span><span class="ed-status info">일정 미공지</span></div>'
          f'<p class="ed-small" style="margin-top:12px">{mo}월 대회 {len(base)}개</p>')
    return h


def main():
    src = json.load(open(os.path.join(ROOT, 'data', 'races.json'), encoding='utf8'))
    pp = os.path.join(ROOT, 'data', 'prior_year.json')
    brp.PRIOR = json.load(open(pp, encoding='utf8')) if os.path.exists(pp) else {}
    R = [brp.adapt(r) for r in src['races']]
    live = [r for r in R if r['st']['key'] != 'ended']
    L = sorted(live, key=lambda r: (RANK[r['st']['key']], r['d']))   # app.js 기본 정렬(접수 중 먼저)
    by = lambda k: sum(1 for r in R if r['st']['key'] == k)
    wk = sum(1 for r in R if 0 <= r['d'] <= 7 and jsdow(r['dt']) in (0, 6))
    t = TODAY
    pre = {}
    F = [('접수중', by('open'), 'data-tab="open"', ''), ('마감임박', by('urgent'), 'data-tab="urgent"', 'accent'), ('접수예정', by('soon'), 'data-tab="soon"', ''), ('이번 주말', wk, 'data-q="wk"', '')]
    pre['figures'] = ''.join(f'<button type="button" class="ed-figure" {a}><b class="{c}">{n}</b><span>{l}</span></button>' for l, n, a, c in F)
    pre['figNote'] = f'{t.month}.{t.day}({WD[jsdow(t)]}) 기준 · 수록 대회 {len(R)}개'
    cnt = {v: (len(live) if v == 'all' else sum(1 for r in live if r['st']['key'] == v)) for v, _ in STAT}
    pre['fStatus'] = chips(STAT, 'status', 'all', cnt)
    pre['fDist'] = chips(DIST, 'dist', '전체')
    regs = ['전체'] + [x for x in REG_ORDER if any(r['region'] == x for r in R)]
    pre['fRegion'] = chips([(v, v) for v in regs], 'region', '전체')
    pre['cal'] = cal_html(L)
    pre['dayBar'] = '<span class="hint">날짜를 누르면 그날의 대회만 아래에 보여요</span>'
    pre['count'] = str(len(L))
    tc = {'all': len(live), 'open': cnt['open'], 'urgent': cnt['urgent'], 'soon': cnt['soon'], 'saved': 0}
    pre['listTabs'] = ''.join(f'<button type="button" data-tab="{k}" class="{"is-on" if k == "all" else ""}" aria-pressed="{"true" if k == "all" else "false"}">{l}<span class="c">{tc[k]}</span></button>'
                              for k, l in [('all', '전체'), ('open', '접수 중'), ('urgent', '마감 임박'), ('soon', '접수 예정'), ('saved', '관심대회')])
    top = L[:HOME_N]
    pre['list'] = ''.join(brp.race_row(r) for r in top)
    # 리드 문장 — 모두 races.json 에서 계산한 값
    n_open = cnt['open'] + cnt['urgent']
    import collections
    bm = collections.Counter(r['start'][:7] for r in live)
    peak = bm.most_common(1)[0] if bm else None
    lede = (f'{t.month}월 {t.day}일({WD[jsdow(t)]}) 기준으로 앞으로 열리는 전국 마라톤·러닝 대회는 <b>{len(live)}개</b>예요. '
            f'지금 접수 중인 대회가 {n_open}개이고, 그중 {cnt["urgent"]}개는 접수 마감이 10일 안으로 다가왔어요. '
            + (f'오늘부터 7일 안의 토·일요일에 열리는 대회는 {wk}개이고, ' if wk else '')
            + (f'대회가 가장 많은 달은 {int(peak[0][:4])}년 {int(peak[0][5:])}월({peak[1]}개)이에요. ' if peak else '')
            + '아래 목록은 접수 중인 대회부터, 대회일이 가까운 순서예요.')
    pre['lede'] = f'<p class="ed-lede lp-lede home-lede">{lede}</p>'
    item_list = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': '다가오는 마라톤·러닝 대회', 'url': SITE + '/', 'numberOfItems': len(top),
          'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': f'{SITE}/race/{r["id"]}.html', 'name': r['name']} for i, r in enumerate(top)]}
    # 값은 사이트에 이미 있는 소개·로고만 쓴다. 검색창(SearchAction)은 JS 필터라 넣지 않는다.
    org = {'@context': 'https://schema.org', '@type': 'Organization', '@id': SITE + '/#organization', 'name': 'Run우리', 'url': SITE + '/',
           'logo': {'@type': 'ImageObject', 'url': SITE + '/assets/logo/icon-any-512.png', 'width': 512, 'height': 512},
           'description': '전국 마라톤·러닝 대회 일정을 한곳에서 확인하고 러닝 가이드를 읽는 개인 프로젝트예요.'}
    website = {'@context': 'https://schema.org', '@type': 'WebSite', '@id': SITE + '/#website', 'name': 'Run우리', 'url': SITE + '/',
               'inLanguage': 'ko-KR', 'description': '날짜·지역·거리·접수 상태로 전국 마라톤 대회를 찾고, 마음에 드는 대회는 저장해 두세요. 참가비와 접수 기간, 공식 홈페이지 링크를 한눈에.',
               'publisher': {'@id': SITE + '/#organization'}}
    pre['ld'] = (f'<script type="application/ld+json">{brp.js(org)}</script>\n'
                 f'<script type="application/ld+json">{brp.js(website)}</script>\n'
                 f'<script type="application/ld+json">{brp.js(item_list)}</script>')
    p = os.path.join(ROOT, 'index.html'); s = open(p, encoding='utf8').read()
    for k, v in pre.items():
        pat = re.compile(r'<!--PRE:' + k + r'-->.*?<!--/PRE:' + k + r'-->', re.S)
        assert pat.search(s), f'index.html 에 PRE:{k} 표시가 없어요'
        s = pat.sub(lambda _m: f'<!--PRE:{k}-->{v}<!--/PRE:{k}-->', s, count=1)
    open(p, 'w', encoding='utf8').write(s)
    print(f'home: 정적 목록 {len(top)}개 / 예정 {len(live)}개 · 접수 중 {n_open} · 달력 {t.year}-{t.month:02d}')


if __name__ == '__main__': main()
