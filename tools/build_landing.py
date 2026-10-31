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

# ── 직접 쓴 안내 문구 ─────────────────────────────────────────────
MONTH_NOTE = {
    1: '1월은 한겨울이라 대회 수가 줄고, 있어도 손이 시린 날씨에 달리는 경우가 많아요. 얇은 겉옷은 출발 전에 벗어 맡길 수 있는지, 장갑과 넥워머를 챙길 수 있는지부터 보세요. 새해 첫 대회로 가볍게 5km나 10km를 고르는 분이 많습니다.',
    2: '2월은 아직 춥지만 해가 길어지기 시작해서 겨울 훈련의 결과를 확인하는 대회가 하나둘 열려요. 땅이 얼거나 눈이 올 수 있어 코스 바닥 상태와 기상 악화 시 일정 변경 공지를 함께 확인해 두세요.',
    3: '3월은 봄 시즌의 시작이에요. 풀코스와 하프 대회가 본격적으로 늘어나는 시기라, 인기 대회는 겨울 사이에 접수가 끝나는 경우가 많습니다. 아침저녁 기온 차가 커서 출발 대기 시간의 체온 관리가 중요해요.',
    4: '4월은 벚꽃 코스가 인기 있는 달이에요. 날씨가 좋아 참가자가 몰리고, 꽃놀이 인파 때문에 주변 교통이 막힐 수 있으니 출발지까지 이동 시간을 넉넉히 잡으세요. 기온이 올라가면서 첫 더위를 겪는 달이기도 합니다.',
    5: '5월은 달리기 좋은 날씨가 이어지는 대표적인 대회 시즌이에요. 대신 한낮에는 기온이 많이 오르는 날이 있으니 오전 출발 대회를 고르고, 수분 보충 지점이 어디에 있는지 코스 안내에서 확인해 두는 편이 좋아요.',
    6: '6월은 장마가 시작되기 전까지가 마지막 선선한 구간이에요. 이후에는 더위와 습도 때문에 기록을 내기 어려워지므로, 이 달 대회는 이른 아침 출발인지 먼저 보세요. 비가 올 경우 진행 여부 공지도 확인하세요.',
    7: '7월은 장마와 폭염 때문에 대회가 적고, 있어도 야간이나 새벽에 여는 대회가 많아요. 기록보다 완주와 안전을 목표로 하고, 열사병 증상이 생기면 바로 멈추는 것을 원칙으로 삼으세요.',
    8: '8월은 한여름이라 일반 도로 마라톤은 거의 열리지 않고, 야간 러닝이나 물놀이를 곁들인 이색 대회가 중심이에요. 더위가 심한 날은 대회가 취소되거나 시간이 바뀔 수 있으니 공지를 자주 확인하세요.',
    9: '9월은 더위가 한풀 꺾이면서 가을 시즌 대회가 다시 늘어나기 시작해요. 아직 낮에는 더운 날이 많아서 초반에는 평소보다 느리게 출발하는 것이 좋고, 가을 대회 접수가 이때부터 열리는 곳이 많습니다.',
    10: '10월은 기온이 달리기에 가장 알맞아 기록을 노리는 사람이 많은 달이에요. 인기 대회는 접수가 빨리 마감되고, 일요일 대회가 특히 많아 출발 지점 주변이 붐빌 수 있어요. 환승·주차 계획을 미리 세워 두세요.',
    11: '11월은 선선한 날씨 덕분에 한 해 중 대회가 가장 많이 몰리는 달이에요. 특히 일요일에 대회가 집중되어 같은 날 여러 대회가 겹치기도 해요. 아침 기온이 한 자릿수로 내려가는 날이 있어 출발 대기 중 보온 준비를 하세요. 접수가 이미 끝난 대회도 많으니 마감일을 먼저 확인하는 것이 좋습니다.',
    12: '12월은 연말 분위기의 이색 대회와 송년 러닝이 많은 달이에요. 11월보다 대회 수는 줄고, 기온이 영하로 내려가는 날도 있어 손과 귀를 보호할 장비가 필요합니다. 크리스마스·송년 대회는 기념품이나 의상 규정이 따로 있는 경우가 있으니 안내를 읽어 보세요.',
}
REGION_NOTE = {
    '서울': '서울의 대회는 안양천 같은 하천변 러닝 트랙, 상암월드컵공원, 여의도공원처럼 평지가 이어지는 곳에서 많이 열려요. 도심 구간을 쓰는 대회는 교통 통제 때문에 지하철로 이동하는 것이 편하고, 짐 보관 시간이 짧은 경우가 있어 출발 전 보관 마감 시각을 확인하는 것이 좋아요.',
    '경기': '경기도는 수도권 접근성이 좋은 호수공원·하천변·임진강 일대 대회가 많아요. 서울 시내보다 코스가 넓어 비교적 한적하게 달릴 수 있지만, 대중교통이 닿지 않는 출발지가 있어 셔틀버스 운행 여부를 확인해 두세요.',
    '인천': '인천은 바다와 맞닿은 송도·영종 일대와 공원 코스에서 대회가 열려요. 바닷바람이 센 날은 체감 온도가 크게 내려가니 겉옷 계획을 세워 두세요.',
    '강원': '강원도는 호수·강변·산악 코스가 다양해 풍경을 즐기며 달리는 대회가 많아요. 고도 변화와 아침 기온이 수도권과 달라서 코스 고저도를 꼭 확인하세요.',
    '충북': '충북은 호수와 강을 낀 코스가 많고 도시 지역과 군 단위 대회가 섞여 있어요. 출발지가 도심에서 먼 경우가 있어 이동 수단을 먼저 확인하세요.',
    '충남': '충남은 서해안과 평야 지대의 평탄한 코스가 많은 편이에요. 바닷가 구간은 바람의 영향이 클 수 있습니다.',
    '대전': '대전은 갑천·유등천 같은 하천 둔치와 엑스포 일대 코스가 중심이에요. 도심에서 가까워 당일 왕복 참가가 쉽습니다.',
    '세종': '세종은 금강과 호수공원 주변의 평탄한 코스를 중심으로 대회가 열려요.',
    '전북': '전북은 만경강·새만금·도심 하천 코스를 중심으로 대회가 열려요. 바람이 센 구간이 있을 수 있습니다.',
    '전남': '전남은 해안과 섬, 지역 축제와 함께 열리는 대회가 많아요. 출발지가 도시 밖에 있는 경우가 많아 숙박과 이동 계획이 필요해요.',
    '광주': '광주는 영산강변과 도심 공원 코스를 중심으로 대회가 열려요.',
    '경북': '경북은 유적지와 강변, 해안 코스를 낀 대회가 있어요. 지역 축제와 날짜가 겹치면 숙박이 빨리 차니 일찍 예약하세요.',
    '경남': '경남은 낙동강변, 해안, 산지가 어우러진 코스가 많아요. 지역마다 기온 차가 있으니 대회 지역의 예보를 따로 확인하세요.',
    '대구': '대구는 금호강변 코스와 도심 공원 코스가 중심이에요. 내륙 분지라 여름에는 더위가 심하고 겨울에는 상대적으로 건조해요.',
    '울산': '울산은 태화강변과 공원 코스를 중심으로 대회가 열려요.',
    '부산': '부산은 광안리·해운대 해변과 낙동강변, 도심 공원 코스에서 대회가 열려요. 해안 도로는 바람이 강한 날 체감 온도가 낮아집니다.',
    '제주': '제주는 해안 도로를 달리는 풍경이 매력이지만 바람의 영향이 커요. 항공편과 숙소를 먼저 잡고 신청하는 편이 안전합니다.',
}

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
        secs.append(section(n, '곧 접수가 시작되는 대회', para('2주 안에 접수가 시작되는 대회예요. 시작일에 정원이 빨리 차는 대회가 있으니 알림을 맞춰 두세요.') + f'<div class="ed-list" style="border-top:0">{rows(soon)}</div>')); n += 1
    guide = ''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a, b in [
        ('마감일 확인', '같은 대회라도 종목마다 마감일이 다르거나, 정원이 차면 마감일 전에 접수가 닫히기도 해요. 목록의 마감일은 참고용이고, 실제로는 대회 공식 접수 페이지의 표시가 기준이에요.'),
        ('마감 당일', '마감 당일 저녁에는 접수 사이트가 느려지거나 결제가 늦어질 수 있어요. 가능하면 하루 전에 신청하고, 마감 시각이 오늘 자정인지 오후 6시 같은 특정 시각인지 확인하세요.'),
        ('결제까지 끝내기', '신청서만 쓰고 참가비 결제나 입금을 마치지 않으면 접수가 완료되지 않는 대회가 많아요. 입금 기한이 신청 마감일보다 짧은 곳도 있습니다.'),
        ('단체·기념품', '단체 접수와 기념품 사이즈 선택은 일반 접수보다 먼저 마감되는 경우가 있어요. 해당된다면 공식 안내의 세부 일정을 따로 보세요.'),
        ('일정 미공지 대회', f'접수 일정이 아직 공개되지 않은 대회는 {len(unk)}개예요. 이런 대회는 대회 날짜가 가까워져도 접수가 열릴 수 있으니 공식 홈페이지 공지를 확인해 주세요.'),
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
    note = para(esc(MONTH_NOTE[m])) + para(f'접수 중인 대회만 보려면 <a class="ed-link" href="deadline.html">마감 임박 대회</a> 페이지를, 지역을 좁히려면 아래 지역별 모아보기를 이용하세요.')
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
    note = para(esc(REGION_NOTE[g]))
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
