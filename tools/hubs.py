"""목록(허브) 페이지 규칙 한 곳 모음 — build_race_pages.py(대회 페이지 breadcrumb·허브 링크)와
build_landing.py(월별·지역별 페이지 생성)가 같은 기준을 쓰도록 여기서만 정한다."""
import collections

MIN_MONTH = 8         # 월별 페이지: 색인 허용 대회 수 최소 (15 → 8, 2026-11-22 SEO P0: 고아 대회 페이지 해소)
MIN_REGION = 15       # 지역별 페이지: 예정 대회 수 최소
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
