"""목록(허브) 페이지 규칙 한 곳 모음 — build_race_pages.py(대회 페이지 breadcrumb·허브 링크)와
build_landing.py(월별·지역별 페이지 생성)가 같은 기준을 쓰도록 여기서만 정한다."""
import collections

MIN_MONTH = 8         # 월별 페이지: 색인 허용 대회 수 최소 (15 → 8, 2026-11-22 SEO P0: 고아 대회 페이지 해소)
MIN_REGION = 8        # 지역별 페이지: 예정 대회 수 최소 (15 → 8, SEO P1 2026-11-22: 서울·경기·충남)
REGIONS = {'서울': 'seoul', '경기': 'gyeonggi', '인천': 'incheon', '강원': 'gangwon', '충북': 'chungbuk', '충남': 'chungnam', '대전': 'daejeon', '세종': 'sejong',
           '전북': 'jeonbuk', '전남': 'jeonnam', '광주': 'gwangju', '경북': 'gyeongbuk', '경남': 'gyeongnam', '대구': 'daegu', '울산': 'ulsan', '부산': 'busan', '제주': 'jeju'}


def months_of(r):
    y, m = int(r['start'][:4]), int(r['start'][5:7])
    ey, em = int(r['end'][:4]), int(r['end'][5:7])
    while (y, m) <= (ey, em):
        yield f'{y:04d}-{m:02d}'
        m += 1
        if m > 12:
            m, y = 1, y + 1


def month_keys(allr):
    """allr: 색인 허용 대회(종료 포함) {id: adapted}. 대회 수가 MIN_MONTH 이상인 달만."""
    c = collections.Counter()
    for r in allr.values():
        for k in months_of(r):
            c[k] += 1
    return sorted(k for k, v in c.items() if v >= MIN_MONTH)


def region_keys(cur):
    """cur: 이번 수집 목록의 대회 {id: adapted}. 예정 대회가 MIN_REGION 이상인 지역만(많은 순)."""
    c = collections.Counter(r['region'] for r in cur.values() if r['st']['key'] != 'ended' and r['region'] in REGIONS)
    return [g for g, v in c.most_common() if v >= MIN_REGION]


# ── SEO P1 (2026-11-22): 연도·거리·접수 중 허브 ─────────────────────────
MIN_HUB = 8           # 연도·거리·접수 중 페이지: 이보다 적으면 noindex + 사이트맵 제외(얇은 페이지 방지)
MIN_FULL = 10         # 풀코스는 계획서 기준 10개 이상일 때만 색인
DISTS = [('half', '하프', '하프 마라톤', '21.0975km'), ('10k', '10K', '10km', '10km'), ('5k', '5K', '5km', '5km'), ('full', '풀', '풀코스 마라톤', '42.195km')]
DIST_BY_TAG = {t: (slug, label, km) for slug, t, label, km in DISTS}


def year_keys(allr):
    """색인 허용 대회(종료 포함)가 MIN_HUB 개 이상인 해."""
    c = collections.Counter(r['start'][:4] for r in allr.values())
    return sorted(y for y, v in c.items() if v >= MIN_HUB)


def dist_counts(cur):
    return collections.Counter(t for r in cur.values() if r['st']['key'] != 'ended' for t in r['distTags'])


def dist_indexable(cur):
    """색인할 거리 페이지 태그 집합(예정 대회 수 기준)."""
    c = dist_counts(cur)
    return {t for _, t, _, _ in DISTS if c.get(t, 0) >= (MIN_FULL if t == '풀' else MIN_HUB)}


def open_count(cur):
    return sum(1 for r in cur.values() if r['st']['key'] in ('open', 'urgent'))


# 지역 슬러그 → 한글 (REGIONS 의 역방향)
REGION_LABEL = {v: k for k, v in REGIONS.items()}


def footer_hubs(pages, today):
    """푸터 '대회 모아보기' 링크. 색인되는 랜딩만, 검색 수요가 큰 월·지역·마감 임박을 포함한다.
    pages: landing_pages.json 의 pages 목록. today: datetime.date."""
    by = {p['path']: p for p in pages if p.get('indexable')}
    out = []

    def add(path, label):
        if path not in {h for h, _ in out}:
            out.append(('/' + path, label))

    years = []
    for p in pages:
        path = p.get('path') or ''
        if p.get('indexable') and path.startswith('marathon-schedule/') and path.endswith('.html'):
            y = path[len('marathon-schedule/'):-5]
            if y.isdigit() and y not in years:
                years.append(y)
    for y in sorted(years):
        add(f'marathon-schedule/{y}.html', f'{y} 마라톤 일정')
    if 'open.html' in by:
        add('open.html', '접수 중인 대회')
    if 'deadline.html' in by:
        add('deadline.html', '마감 임박')
    y, m = today.year, today.month
    for _ in range(3):
        key = f'{y:04d}-{m:02d}'
        path = f'month/{key}.html'
        if path in by:
            label = f'{m}월 마라톤' if y == today.year else f'{y}년 {m}월 마라톤'
            add(path, label)
        m += 1
        if m > 12:
            m, y = 1, y + 1
    for slug in ('seoul', 'gyeonggi', 'incheon', 'busan', 'daegu', 'gwangju', 'daejeon', 'ulsan',
                 'gangwon', 'chungbuk', 'chungnam', 'sejong', 'jeonbuk', 'jeonnam', 'gyeongbuk', 'gyeongnam', 'jeju'):
        path = f'region/{slug}.html'
        if path in by:
            add(path, f'{REGION_LABEL[slug]} 마라톤')
    for slug, lab in (('half', '하프'), ('10k', '10km'), ('5k', '5km'), ('full', '풀코스')):
        path = f'distance/{slug}.html'
        if path in by:
            add(path, lab)
    # 도구·가이드 허브는 랜딩 json 과 무관하게 유지
    for path, lab in (('tools/pace-calculator.html', '페이스 계산기'), ('shoes/', '러닝화'), ('gear/', '러닝 복장')):
        if path not in {h.lstrip('/') for h, _ in out}:
            out.append(('/' + path if not path.startswith('/') else path, lab))
    return out
