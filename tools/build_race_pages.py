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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import weather_lib   # 대회 날씨 예보 표시 (data/weather.json 이 없으면 아무것도 표시하지 않는다)

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


# ── 시·군·구 (SEO: 제목·설명·본문 첫 문장·JSON-LD addressLocality) ──
# 데이터에 시·군·구 칸이 없어서 ① 장소(venue) 글자 ② 장소 지오코딩 캐시(data/venue_geo.json, OSM 주소) ③ 대회 이름 순으로 찾는다.
# 해당 시·도에 실제로 있는 시·군·구 이름과 맞을 때만 쓰고, 못 찾으면 시·도만 쓴다(지어내지 않음).
_LOCAL_SRC = {
    '서울': '종로구 중구 용산구 성동구 광진구 동대문구 중랑구 성북구 강북구 도봉구 노원구 은평구 서대문구 마포구 양천구 강서구 구로구 금천구 영등포구 동작구 관악구 서초구 강남구 송파구 강동구',
    '부산': '중구 서구 동구 영도구 부산진구 동래구 남구 북구 해운대구 사하구 금정구 강서구 연제구 수영구 사상구 기장군',
    '대구': '중구 동구 서구 남구 북구 수성구 달서구 달성군 군위군',
    '인천': '중구 동구 미추홀구 연수구 남동구 부평구 계양구 서구 제물포구 영종구 서해구 검단구 강화군 옹진군',
    '광주': '동구 서구 남구 북구 광산구',
    '대전': '동구 중구 서구 유성구 대덕구',
    '울산': '중구 남구 동구 북구 울주군',
    '세종': '',
    '경기': '수원시 성남시 의정부시 안양시 부천시 광명시 평택시 동두천시 안산시 고양시 과천시 구리시 남양주시 오산시 시흥시 군포시 의왕시 하남시 용인시 파주시 이천시 안성시 김포시 화성시 광주시 양주시 포천시 여주시 연천군 가평군 양평군',
    '강원': '춘천시 원주시 강릉시 동해시 태백시 속초시 삼척시 홍천군 횡성군 영월군 평창군 정선군 철원군 화천군 양구군 인제군 고성군 양양군',
    '충북': '청주시 충주시 제천시 보은군 옥천군 영동군 증평군 진천군 괴산군 음성군 단양군',
    '충남': '천안시 공주시 보령시 아산시 서산시 논산시 계룡시 당진시 금산군 부여군 서천군 청양군 홍성군 예산군 태안군',
    '전북': '전주시 군산시 익산시 정읍시 남원시 김제시 완주군 진안군 무주군 장수군 임실군 순창군 고창군 부안군',
    '전남': '목포시 여수시 순천시 나주시 광양시 담양군 곡성군 구례군 고흥군 보성군 화순군 장흥군 강진군 해남군 영암군 무안군 함평군 영광군 장성군 완도군 진도군 신안군',
    '경북': '포항시 경주시 김천시 안동시 구미시 영주시 영천시 상주시 문경시 경산시 의성군 청송군 영양군 영덕군 청도군 고령군 성주군 칠곡군 예천군 봉화군 울진군 울릉군',
    '경남': '창원시 진주시 통영시 사천시 김해시 밀양시 거제시 양산시 의령군 함안군 창녕군 고성군 남해군 하동군 산청군 함양군 거창군 합천군',
    '제주': '제주시 서귀포시',
}
LOCAL = {k: v.split() for k, v in _LOCAL_SRC.items()}
METRO = {'서울', '부산', '대구', '인천', '광주', '대전', '울산'}
_NOT_PLACE = ('동해안',)   # 시 이름으로 시작하지만 지명이 아닌 말


def _base(full): return full[:-1] if len(full) > 2 else full   # 창원시→창원, 중구→중구(한 글자는 그대로)


def _find_local(text, region, allow_base=True):
    if not text: return None
    text = str(text)
    if any(w in text for w in _NOT_PLACE): text = text.replace('동해안', '')
    cands = sorted(LOCAL.get(region, []), key=len, reverse=True)
    pre = r'(?:^|(?<=[^가-힣])|(?<=' + re.escape(region) + r'))'
    for full in cands:                                  # '창원시', '송파구', '대전서구' 같은 정식 이름
        if re.search(pre + re.escape(full), text): return full
    if not allow_base: return None
    for full in cands:                                  # '창원 ...', '남해공설운동장' 처럼 '시·군'을 뺀 이름으로 시작하는 말
        b = _base(full)
        if b == full or len(b) < 2: continue
        if region == '제주' and b == '제주': continue    # '제주도 일원'은 제주시가 아니다
        if region in METRO and full.endswith('구'): continue   # 광역시의 구 이름은 '구'까지 쓴 경우만 인정(예: '강남' 단독은 지역 이름이 아닐 수 있음). 군(기장·울주 등)은 허용
        if re.search(r'(?:^|(?<=[\s(（·,~/]))' + re.escape(b), text): return full
    return None


# 잘 알려진 동네·시설 이름 → 시·군·구 (장소 글자에 시·군·구가 없을 때만, 괄호 앞부분에서만 쓴다)
ALIAS = {'경남': {'진해': '창원시', '마산': '창원시'}, '경기': {'일산': '고양시', '분당': '성남시', '임진각': '파주시'},
         '서울': {'상암': '마포구', '여의도': '영등포구', '잠실': '송파구', '올림픽공원': '송파구', '뚝섬': '광진구', '반포한강': '서초구', '광화문': '종로구'},
         '인천': {'송도': '연수구', '영종': '영종구'}}


def _multi_site(venue):
    head = re.split(r'[(（]', venue or '')[0]
    return '→' in (venue or '') or bool(re.search(r'/|\d+\s*km|하프\s*:|풀코스', head))


def _alias_local(venue, region):
    head = re.split(r'[(（]', venue or '')[0]
    for k, full in ALIAS.get(region, {}).items():
        if re.search(r'(?:^|(?<=[\s·,]))' + re.escape(k), head): return full
    return None


def geo_hit(venue):
    """지오코딩 캐시에서 이 장소와 같은 곳으로 볼 수 있는 결과만 돌려준다(다리 밑·경계 지점, 다른 시설로 잡힌 결과는 버림)."""
    if not venue: return None
    key = venue_query(venue)
    v = GEO.get(key)
    if not v or 'name' not in v: return None
    first = v['name'].split(',')[0].strip()
    if re.search(r'(교|다리|하부)$', first) or re.search(r'교\s*하부', first): return None
    if v.get('q') != key and first.replace(' ', '') not in key.replace(' ', ''): return None
    return v


def _geo_local(venue, region):
    v = geo_hit(venue)
    if not v: return None
    toks = [t.strip() for t in v['name'].split(',')]
    if PROV.get(region) not in toks: return None
    for t in toks:
        if t in LOCAL.get(region, []): return t
    return None


def locality(r):
    """정식 시·군·구 이름(예: '창원시', '송파구') 또는 None."""
    reg = r.get('region') or ''
    if reg not in LOCAL or not LOCAL[reg]: return None
    v = r.get('venue') or ''
    if _multi_site(v): return None if reg in METRO else _find_local(r.get('name'), reg, allow_base=False)   # 출발·도착이 다른 대회: 장소로 한 곳을 정하지 않는다
    # 광역시는 대회 이름의 구 이름이 주최(구청장배 등)일 때가 많아 이름으로는 정하지 않는다
    return (_find_local(v, reg) or _alias_local(v, reg) or _geo_local(v, reg) or (None if reg in METRO else _find_local(r.get('name'), reg)))


def loc_label(r):
    """사람이 읽는 지역 이름: '경남 창원', '서울 송파구', '제주 서귀포', '세종'. 온라인·전국이면 ''."""
    reg = r.get('region') or ''
    if not reg or reg == '전국': return ''
    loc = r.get('locality')
    if not loc: return reg
    if reg in METRO: return f'{reg} {loc}'
    b = _base(loc)
    return loc if b == reg else f'{reg} {b}'


def loc_short(r):
    """제목용 짧은 지역 이름: '창원', '송파구', '서울'."""
    reg = r.get('region') or ''
    if not reg or reg == '전국': return ''
    loc = r.get('locality')
    if not loc: return reg
    return f'{reg} {loc}' if reg in METRO else (loc if _base(loc) == reg else _base(loc))


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


WX = weather_lib.load()   # data/weather.json (tools/fetch_weather.py 산출물)
_gp = os.path.join(ROOT, 'data', 'venue_geo.json')
GEO = json.load(open(_gp, encoding='utf8')) if os.path.exists(_gp) else {}   # tools/geocode_venues.py 캐시(시·군·구 찾기·좌표)
PRIOR = {}   # data/prior_year.json: 올해 접수 일정이 없는 대회의 '작년 접수' 참고값 (main 에서 읽음)


def prior_text(p):
    if not p: return ''
    f = lambda s: pd(s)
    o, c = p.get('open'), p.get('close')
    if o and c:
        a, b = f(o), f(c)
        rng = f'{a.year}.{a.month}.{a.day}~{b.month}.{b.day}' if a.year == b.year else f'{a.year}.{a.month}.{a.day}~{b.year}.{b.month}.{b.day}'
    elif o: a = f(o); rng = f'{a.year}.{a.month}.{a.day}~'
    elif c: b = f(c); rng = f'~{b.year}.{b.month}.{b.day}'
    else: return ''
    return f'작년 접수 {rng} (참고)'


def unannounced(r):
    t = prior_text(r.get('prior'))
    return '접수 일정 미공지' + (f' · {t}' if t else '')


def event_span(r):
    start = r.get('start') or r.get('date')
    end = r.get('end') or r.get('end_date') or start
    return start, end


def is_cancelled(r):
    if r.get('eventStatus') in ('EventCancelled', 'cancelled', 'https://schema.org/EventCancelled') or r.get('event_status') in ('EventCancelled', 'cancelled', 'https://schema.org/EventCancelled'): return True
    text = (r.get('name') or '') + ' ' + (r.get('regNote') or r.get('reg_note') or '')
    return '개최 취소' in text or '대회 취소' in text


def is_ongoing(r, today=None):
    today = (today or TODAY).isoformat() if hasattr(today or TODAY, 'isoformat') else (today or TODAY)
    start, end = event_span(r)
    return start < end and start <= today <= end


def adapt(r):
    start, end = r['date'], r.get('end_date') or r['date']
    ongoing = is_ongoing({'start': start, 'end': end})
    dists = r.get('distances') or []
    a = dict(id=r['id'], name=r['name'], start=start, end=end, date=start, ongoing=ongoing,
             region=r.get('region') or '', venue=r.get('venue') or '', organizer=r.get('organizer') or '', type=r.get('category') or '',
             distances=dists, distTags=r.get('dist_tags') or [], fee=fee_range(r), fee_min=r.get('fee_min'), fee_max=r.get('fee_max'),
             open=r.get('reg_open'), close=r.get('reg_close'), regState=r.get('reg_state'), regNote=r.get('reg_note'),
             official=r.get('official_url'), regUrl=r.get('reg_url'), sources=r.get('sources') or {}, startTime=r.get('start_time'), verified=r.get('verified'),
             prior=(PRIOR.get(r['id']) if not (r.get('reg_open') or r.get('reg_close')) else None))
    a['dist'] = [d['label'] for d in dists]
    a['eventStatus'] = r.get('event_status') or r.get('eventStatus')
    a['locality'] = locality(r)
    start_d, end_d = pd(start), pd(end)
    past = end_d < TODAY
    a['d'] = ((end_d if past or ongoing else start_d) - TODAY).days
    a['dt'] = end_d if past else start_d
    a['regSt'] = reg_status(a)
    a['st'] = status(a)
    return a


def reg_status(r):
    t, op, cl = TODAY, pd(r['open']), pd(r['close'])
    if r['regState'] == 'full': return dict(key='closed', label='정원 마감')
    if r['regState'] == 'suspended': return dict(key='closed', label='접수 중단')
    if cl and cl < t: return dict(key='closed', label='마감')
    if r['regState'] == 'closed': return dict(key='closed', label='마감')
    if op and op > t: return dict(key='soon', label='접수예정')
    if r['regState'] == 'upcoming': return dict(key='soon', label='접수예정')
    if cl and (cl - t).days <= URGENT_DAYS: return dict(key='urgent', label='마감임박')
    if cl or op or r['regState'] in ('open', 'ongoing'): return dict(key='open', label='접수중')
    return dict(key='info', label='일정 미공지')


def status(r):
    end = pd(event_span(r)[1])
    if end < TODAY: return dict(key='ended', label='종료')
    if r.get('ongoing') or is_ongoing(r): return dict(key='ongoing', label='진행 중')
    return reg_status(r)


def reg_text(r):
    t = TODAY
    if r['ongoing']: return f"진행 중 · ~{fmt_short(pd(r['end']))} 까지"
    k = r['st']['key']
    if k == 'soon' and r['open']: return f"접수 {fmt_short(pd(r['open']))} 시작 (D-{(pd(r['open']) - t).days})"
    if k == 'soon': return unannounced(r)
    if r['close'] and k != 'closed': return f"접수 ~{fmt_short(pd(r['close']))} (D-{(pd(r['close']) - t).days})"
    if r['close']: return f"접수 마감 {fmt_short(pd(r['close']))}"
    if k == 'closed': return '접수 마감'
    if k == 'info': return unannounced(r)
    return '마감일 미공지'


def dday_cls(r):
    if r['st']['key'] in ('closed', 'ended', 'ongoing'): return ''
    return 'soon' if (r['st']['key'] == 'urgent' or 0 <= r['d'] <= 7) else ''


BM = '<svg viewBox="0 0 18 22" aria-hidden="true"><path d="M3 2.5h12v17.2l-6-4.2-6 4.2z"/></svg>'
SEP = '<span class="sep">·</span>'


def race_row(r):
    dist = ' · '.join(r['dist'][:3]) + (f" 외 {len(r['dist']) - 3}개" if len(r['dist']) > 3 else '') if r['dist'] else '종목 확인 필요'
    meta1 = SEP.join(x for x in [esc(r['region'] or '지역 확인 필요'), esc(r['type']) if r['type'] else '', esc(dist)] if x)
    fee = r['fee'] or '참가비 확인 필요'
    return (f'<article class="ed-race" data-id="{r["id"]}">'
            f'<div class="ed-race-date"><b>{r["dt"].day:02d}</b><span>{r["dt"].month}월 {wd(r["dt"])}</span></div>'
            f'<div class="ed-race-body"><div class="ed-race-top"><span class="ed-status {r["st"]["key"]}">{r["st"]["label"]}</span>{weather_lib.chip(WX, r["id"], TODAY)}</div>'
            f'<h3><a class="row-link" href="race/{r["id"]}.html">{esc(r["name"])}</a></h3>'
            f'<p class="ed-meta">{meta1}</p><p class="ed-meta">{esc(reg_text(r))}{SEP}{esc(fee)}</p></div>'
            f'<div class="ed-race-side"><div class="ed-dday {dday_cls(r)}>{"진행 중" if r["ongoing"] or r["st"]["key"] == "ongoing" else dday_text(r["d"])}</div>'
            f'<button class="ed-bookmark" aria-pressed="false" aria-label="관심 대회 저장" data-fav="{r["id"]}">{BM}</button></div></article>')


def read_snippet(name):
    """내용 페이지(about.html)의 AdSense 조각과 index.html 의 GA4 조각을 읽는다.

    홈·계산기·개인 화면은 광고를 넣지 않으므로(head_snippets.AD_FREE) index.html 의
    AdSense 켜짐/꺼짐을 생성 페이지에 복사하지 않는다. GA4 는 계속 index.html 을 따른다.
    """
    import head_snippets
    return head_snippets.adsense_and_ga4(ROOT)


def js(o): return json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')


def _josa(word, with_final, without_final):
    """받침 여부에 맞는 조사. 영문·숫자로 끝나면 읽는 소리로 어림한다."""
    w = re.sub(r'\s*[(（][^()（）]*[)）]\s*$', '', str(word or '')).strip() or str(word or '')
    ch = w[-1:] if w else ''
    if '가' <= ch <= '힣': return with_final if (ord(ch) - 0xAC00) % 28 else without_final
    if ch.isdigit(): return with_final if ch in '013678' else without_final
    if ch.lower() in 'aeiouyw': return without_final
    return with_final if ch.isalpha() else without_final


def venue_short(r):
    v = re.split(r'[(（]', r.get('venue') or '')[0].strip(' ,·')
    if not v or v in ('미정', '추후 공지') or '온라인' in v or '어디서나' in v: return ''
    return v


def is_online(r):
    v = r.get('venue') or ''
    return '온라인' in v or '어디서나' in v or r.get('region') == '전국' or r.get('type') == '버추얼'


def is_rescheduled(r): return '연기' in (r.get('name') or '') and not is_cancelled(r)


def kind_word(r):
    t, n = r.get('type') or '', r.get('name') or ''
    if t == '트레일' or '트레일' in n: return '트레일런'
    if t == '버추얼': return '버추얼런'
    if t == '걷기' or '걷기' in n or '워크' in n.lower(): return '걷기·달리기 대회'
    if '마라톤' in n: return '마라톤'
    return '러닝 대회'


def where_text(r):
    """'경남 창원 광려천 공원 일원'처럼 지역 + 장소. 장소 글자가 이미 지역 이름으로 시작하면 겹치지 않게 줄인다."""
    loc, v = loc_label(r), venue_short(r)
    if _multi_site(r.get('venue') or ''): v = ''
    if not v: return loc
    if not loc: return v
    reg = r.get('region') or ''
    lc = r.get('locality') or ''
    for p in filter(None, [PROV.get(reg), reg]):
        if v.startswith(p): return v                                         # '서울 올림픽공원', '경기도 하남시 …'
    if lc and (lc in v or v.startswith(_base(lc))): return f'{reg} {v}'
    return f'{loc} {v}'


def kdate(s):
    d = pd(s); return f'{d.year}년 {d.month}월 {d.day}일({wd(d)})'


def name_year(r):
    y = r['start'][:4]
    return r['name'] if y in r['name'] else f"{r['name']} {y}"


def page_title(r):
    base = name_year(r)
    loc = loc_short(r)
    kw = kind_word(r)
    if is_online(r): mids = [f'{kw} 접수·일정', '접수·일정']
    elif loc: mids = [f'{loc} {kw} 접수·일정·코스', f'{loc} {kw} 접수·일정', f'{loc} {kw}', '접수·일정']
    else: mids = [f'{kw} 접수·일정·코스', '접수·일정']
    for m in mids:
        t = f'{base} — {m} | Run우리'
        if len(t) <= 60: return t
    return f'{base} | Run우리'


def reg_phrase(r):
    """설명·첫 문장에 쓰는 접수 상태(생성 시점 기준)."""
    k = r['regSt']['key']; op, cl = r['open'], r['close']
    if k == 'urgent' and cl: return f"접수 마감 임박({fmt_short(pd(cl))}까지)"
    if k == 'open': return f"접수 중({fmt_short(pd(cl))}까지)" if cl else '접수 중'
    if k == 'soon' and op: return f"접수 {fmt_short(pd(op))} 시작 예정"
    if k == 'closed': return r['regSt']['label'] if r['regSt']['label'] != '마감' else '접수 마감'
    return '접수 일정 미공지'


def description(r):
    date_txt = fmt_full(pd(r['start'])) + (f" ~ {fmt_full(pd(r['end']))}" if r['start'] != r['end'] else '')
    where = where_text(r)
    if is_cancelled(r): verb = '열릴 예정이던'
    elif r['st']['key'] == 'ended': verb = '열린'
    elif is_online(r): verb = '참가하는'
    else: verb = '열리는'
    if is_online(r): lead = f"{date_txt} 원하는 곳에서 {verb} {r['name']}"
    else: lead = f"{date_txt} {where}에서 {verb} {r['name']}" if where else f"{date_txt} {verb} {r['name']}"
    facts = []
    dl = list(dict.fromkeys(r['dist']))   # 같은 이름 종목(예: 5km 두 부문)은 한 번만
    if dl: facts.append('종목 ' + '·'.join(dl[:3]) + (' 등' if len(dl) > 3 else ''))
    if r['fee']: facts.append('참가비 ' + r['fee'])
    if is_cancelled(r): tail = '개최가 취소된 대회예요.'
    elif r['st']['key'] == 'ended': tail = '이미 끝난 대회예요.'
    elif r['ongoing'] or r['st']['key'] == 'ongoing': tail = f"지금 진행 중이에요(~{fmt_short(pd(r['end']))}까지)."
    else: tail = reg_phrase(r) + '.'
    for n in (len(facts), 1, 0):
        s = f"{lead}. " + (', '.join(facts[:n]) + '. ' if n else '') + tail
        if len(s) <= 155: return s
    return s if len(s) <= 155 else s[:152].rstrip(' ·,.') + '…'


def lead_html(r):
    """본문 맨 앞 한두 문장: 대회 이름 + 지역 + 날짜 + 장소 + 종목·참가비·접수를 자연스러운 문장으로."""
    nm = r['name']
    date_txt = kdate(r['start']) + (f"부터 {kdate(r['end'])}까지" if r['start'] != r['end'] else '')
    where = where_text(r)
    at = f"{where}에서 " if where and not is_online(r) else ('원하는 곳에서 달리는 방식으로 ' if is_online(r) else '')
    subj = nm + _josa(nm, '은', '는')
    if is_cancelled(r): s1 = f"{subj} {date_txt} {at}열릴 예정이었지만 개최가 취소됐어요."
    elif r['st']['key'] == 'ended': s1 = f"{subj} {date_txt} {at}열린 대회예요."
    elif r['ongoing'] or r['st']['key'] == 'ongoing': s1 = f"{subj} {date_txt} {at}열리고 있어요."
    else: s1 = f"{subj} {date_txt} {at}열려요."
    parts = [s1]
    dl = list(dict.fromkeys(r['dist']))
    if dl and r['fee']:
        parts.append(f"{', '.join(dl[:5])} 종목이 있고, 참가비는 {r['fee']}{_josa(r['fee'], '이에요', '예요')}.")
    elif dl: parts.append(f"{', '.join(dl[:5])} 종목이 있어요.")
    elif r['fee']: parts.append(f"참가비는 {r['fee']}{_josa(r['fee'], '이에요', '예요')}.")
    if not is_cancelled(r) and r['st']['key'] not in ('ended', 'ongoing') and not r['ongoing']:
        k = r['regSt']['key']; op, cl = r['open'], r['close']
        if k == 'urgent' and cl: parts.append(f"접수는 {fmt_short(pd(cl))}에 마감이라 얼마 안 남았어요.")
        elif k == 'open': parts.append(f"지금 접수 중이고 {fmt_short(pd(cl))}에 마감해요." if cl else '지금 접수 중이에요.')
        elif k == 'soon' and op: parts.append(f"접수는 {fmt_short(pd(op))}에 시작해요.")
        elif k == 'closed': parts.append('정원이 차서 접수가 마감됐어요.' if r['regState'] == 'full' else '접수는 마감됐어요.')
        else: parts.append('접수 일정은 아직 공지되지 않았어요.')
    return f'<p class="ed-small race-lead" style="line-height:1.8;margin:10px 0 0">{esc(" ".join(parts))}</p>'


_ROAD = re.compile(r'[가-힣0-9]+(?:로|길)\s*\d+(?:[-–]\d+)?(?:번길\s*\d+(?:-\d+)?)?')


def street_address(r):
    """장소 괄호 안에 도로명·지번 주소가 적혀 있을 때만 그대로 쓴다."""
    m = re.search(r'[(（]([^()（）]+)[)）]', r.get('venue') or '')
    cand = m.group(1) if m else ''
    if not cand:
        v = r.get('venue') or ''
        if re.search(r'(시|군|구)\s', v) and (_ROAD.search(v) or re.search(r'[동리]\s*\d+(-\d+)?$', v)): cand = v
    cand = cand.strip()
    if cand and (_ROAD.search(cand) or re.search(r'[동리가]\s*\d+(-\d+)?$', cand) or re.search(r'(시|군|구)\s.*[가-힣](읍|면|동|리)(\s|$)', cand)): return cand
    return None


def json_ld(r, url, official, reg):
    online = is_online(r) or str(r.get('eventStatus') or '').rsplit('/', 1)[-1] in ('EventMovedOnline', 'moved_online')
    start = r['start'] + (f"T{r['startTime']}:00+09:00" if r['startTime'] and re.match(r'^\d\d:\d\d$', r['startTime']) else '')
    explicit = str(r.get('eventStatus') or '').rsplit('/', 1)[-1]
    mapped = {'cancelled': 'EventCancelled', 'postponed': 'EventPostponed', 'rescheduled': 'EventRescheduled', 'moved_online': 'EventMovedOnline'}
    explicit = mapped.get(explicit, explicit)
    allowed = {'EventScheduled', 'EventCancelled', 'EventPostponed', 'EventRescheduled', 'EventMovedOnline'}
    status_url = explicit if explicit in allowed else ('EventCancelled' if is_cancelled(r) else 'EventRescheduled' if is_rescheduled(r) else 'EventScheduled')
    ld = {'@context': 'https://schema.org', '@type': 'SportsEvent', 'name': r['name'], 'description': description(r),
          'startDate': start, 'endDate': r['end'],
          'eventStatus': 'https://schema.org/' + status_url,
          'url': url, 'image': [SITE + '/assets/icons/og-image.png'], 'inLanguage': 'ko-KR', 'sport': 'Running'}
    if online:
        ld['eventAttendanceMode'] = 'https://schema.org/OnlineEventAttendanceMode'
        ld['location'] = {'@type': 'VirtualLocation', 'url': official or url}
    else:
        ld['eventAttendanceMode'] = 'https://schema.org/OfflineEventAttendanceMode'
        addr = {'@type': 'PostalAddress', 'addressCountry': 'KR'}
        if r['region'] in PROV: addr['addressRegion'] = PROV[r['region']]
        if r.get('locality'): addr['addressLocality'] = r['locality']
        sa = street_address(r)
        if sa: addr['streetAddress'] = sa
        vs = venue_short(r) if not _multi_site(r['venue']) else ''
        place = {'@type': 'Place', 'name': vs or r['venue'] or loc_label(r) or r['region'] or '장소 미정', 'address': addr}
        g = geo_hit(r['venue']) if vs else None
        if g and g.get('q') == venue_query(r['venue']):
            place['geo'] = {'@type': 'GeoCoordinates', 'latitude': g['lat'], 'longitude': g['lng']}
        ld['location'] = place
    if r['organizer']: ld['organizer'] = {'@type': 'Organization', 'name': r['organizer'], **({'url': official} if official else {})}
    if official: ld['sameAs'] = [official]
    k = r['regSt']['key']
    avail = {'open': 'InStock', 'urgent': 'InStock', 'soon': 'PreOrder', 'closed': 'SoldOut'}.get(k)
    if r['regState'] == 'full' and k != 'ended': avail = 'SoldOut'
    if is_cancelled(r): avail = None
    def offer(**kw):
        o = {'@type': 'Offer', **kw, 'priceCurrency': 'KRW', 'url': official or reg or url}
        if avail: o['availability'] = 'https://schema.org/' + avail
        if r['open']: o['validFrom'] = r['open'] + 'T00:00:00+09:00'
        if r['close']: o['validThrough'] = r['close'] + 'T23:59:59+09:00'
        return o
    offers = [offer(name=d['label'], price=d['fee']) for d in r['distances'] if d.get('fee') is not None]
    if offers: ld['offers'] = offers
    elif r.get('fee_min') is not None:
        o = offer(price=r['fee_min']); o['@type'] = 'AggregateOffer'; o['lowPrice'] = o.pop('price')
        if r.get('fee_max') is not None: o['highPrice'] = r['fee_max']
        ld['offers'] = o
    subs = [{'@type': 'SportsEvent', 'name': f"{r['name']} {d['label']}", 'startDate': start, 'sport': 'Running',
             'location': ld['location'], 'eventAttendanceMode': ld['eventAttendanceMode'],
             'eventStatus': ld['eventStatus']} for d in r['distances'] if d.get('label')]
    if len(subs) > 1: ld['subEvent'] = subs
    return ld


PREP_POSTS = {  # 거리 구간 → (권장 준비 주수, 읽어 볼 가이드 글)
    '5K':   (8,  [('beginner-5k-plan', '초보자 5km 완주 훈련 계획')]),
    '10K':  (8,  [('10k-training-plan', '10km 대회 준비: 8주 훈련 계획')]),
    '하프': (12, [('half-marathon-prep', '하프마라톤 준비: 12주 훈련 구조')]),
    '풀':   (16, [('marathon-prep-and-taper', '풀코스 준비와 테이퍼링'), ('first-marathon-checklist', '마라톤 첫 참가 준비 순서')]),
}
PREP_COMMON = [('first-marathon-checklist#gear', '대회 준비물 점검'), ('first-marathon-checklist#raceday', '대회 전날·당일 루틴')]  # 2026-11-11 병합: 옛 race-gear-checklist·race-day-routine → 첫 참가 준비 글의 해당 절


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
    links = ''.join(f'<li><a class="ed-link" href="guide/{i.split("#")[0]}.html{"#" + i.split("#")[1] if "#" in i else ""}">{esc(t)}</a></li>' for i, t in posts)
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
    title = page_title(r)
    desc = description(r)
    date_txt = f"{fmt_full(pd(r['start']))} ~ {fmt_full(pd(r['end']))}" if r['start'] != r['end'] else fmt_full(r['dt'])
    if r['open'] or r['close']:
        reg_period = f"{fmt_full(pd(r['open'])) if r['open'] else '시작일 미확인'} ~ {fmt_full(pd(r['close'])) if r['close'] else '정원 마감 시까지'}"
    elif r['st']['key'] in ('soon', 'info'): reg_period = unannounced(r)
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
    <h1 class="ed-h1" style="margin:14px 0 8px">{esc(r['name'])}{(' — ' + esc(loc_label(r))) if loc_label(r) and not is_online(r) else ''}</h1>
    <p class="ed-lede">{date_txt}{f" · 출발 {esc(r['startTime'])}" if r['startTime'] else ''}{f" · {esc(r['venue'])}" if r['venue'] else ''}{f" ({esc(region if (r.get('locality') and _base(r['locality']) in (r['venue'] or '')) else (loc_label(r) or region))})" if region else ''}</p>
    {lead_html(r)}
    <div class="ed-actions" style="display:flex;flex-wrap:wrap;gap:10px;margin:22px 0 0">
      {f'<a class="ed-btn" href="{esc(official)}" target="_blank" rel="noopener noreferrer">공식 홈페이지 <span class="ed-arrow">↗</span></a>' if official else ''}
      {f'<a class="ed-btn ghost" href="{esc(reg)}" target="_blank" rel="noopener noreferrer">접수 페이지 <span class="ed-arrow">↗</span></a>' if reg else ''}
      <button type="button" class="ed-btn ghost ed-savebtn" data-fav="{r['id']}" aria-pressed="false"><span class="off">북마크 저장</span><span class="on">저장됨</span></button>
    </div>
    {weather_lib.panel(WX, r['id'], TODAY)}
    {ver_badge}{official_note}
    <p class="ed-small" style="margin-top:14px;display:flex;flex-wrap:wrap;gap:6px 18px">
      <a class="ed-link" href="tools.html?date={r['date']}">이 대회로 훈련 계획 만들기</a>
      <button type="button" class="ed-link ed-textbtn" id="ics">캘린더에 추가(.ics)</button>
      <button type="button" class="ed-link ed-textbtn" id="share" hidden>공유</button>
      <button type="button" class="ed-link ed-textbtn" id="copy">링크 복사</button>
      {naver}</p>
  </header>
  <div class="ed-cols" style="margin-top:36px">
    <section class="ed-section"><div class="ed-section-head major"><span class="no">01</span><h2 class="ed-h2">대회 정보</h2></div>
      <dl class="ed-dl">{row('대회일', date_txt, 'serif')}{row('장소', esc(r['venue']))}{row('지역', esc(region))}{row('주최', esc(r['organizer']))}{row('출발', esc(r['startTime'] or ''))}{row('참가비', esc(r['fee']))}</dl></section>
    <section class="ed-section"><div class="ed-section-head major"><span class="no">02</span><h2 class="ed-h2">접수</h2></div>
      <dl class="ed-dl">{row('상태', f'<span class="ed-status {r["regSt"]["key"]}">{r["regSt"]["label"]}</span>')}{row('접수 기간', esc(reg_period))}{row('안내', esc(reg_text(r)))}</dl>
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
  $('#ics').onclick=()=>RW.addToCalendar(r);
  if(RW.native) $('#ics').textContent='캘린더에 추가';
  if(RW.native||navigator.share){{ const sb=$('#share'); sb.hidden=false; sb.onclick=()=>RW.share({{title:r.name+' | Run우리',text:r.name+' 대회 일정',url:location.origin+location.pathname}}); }}
  $('#copy').onclick=()=>{{ const u=location.origin+location.pathname; (navigator.clipboard?navigator.clipboard.writeText(u):Promise.reject()).then(()=>toast('링크를 복사했어요'),()=>toast('복사하지 못했어요. 주소창의 주소를 복사해 주세요')); }};
}})();
</script></body></html>
'''
    head = HEAD.format(title=esc(title), desc=esc(desc), robots='index,follow' if indexable else 'noindex,follow', url=url, site=SITE,
                       adsense=adsense, ld=js(json_ld(r, url, official, reg)), crumbs=js(crumb_ld))
    return head + body


def main():
    global PRIOR
    pp = os.path.join(ROOT, 'data', 'prior_year.json')
    PRIOR = json.load(open(pp, encoding='utf8')) if os.path.exists(pp) else {}
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
