#!/usr/bin/env python3
"""대회 장소(venue)를 OSM Nominatim 으로 지오코딩해 data/venue_geo.json 캐시에 '새 장소만' 추가한다.

  python3 tools/geocode_venues.py            # 새 장소만 처리 (하루 루틴용)
  python3 tools/geocode_venues.py --retry    # 이전에 실패(fail)로 저장된 장소도 다시 시도
  python3 tools/geocode_venues.py --max 80   # 한 번에 처리할 새 장소 수 상한 (기본 80)

- 캐시 키 = app.js 의 venueQuery() 와 같은 규칙으로 정리한 장소 문자열.
- 값: {"lat":..,"lng":..,"q":"검색어","name":"매칭 이름"}  또는 실패 {"fail":"YYYY-MM-DD"}
  (실패는 30일 뒤 자동 재시도. 네트워크 오류는 캐시에 남기지 않고 다음 실행에서 재시도)
- 온라인/전국 대회, 지역(시·도) 범위를 벗어난 결과, 불확실한 결과는 좌표를 넣지 않는다.
- Nominatim 정책: 초당 1회 이하, 식별 가능한 User-Agent.
"""
import argparse, datetime, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACES = os.path.join(ROOT, 'data', 'races.json')
CACHE = os.path.join(ROOT, 'data', 'venue_geo.json')
UA = 'runwoori-site/1.0 (runwoori@gmail.com)'
RETRY_DAYS = 30

# 시·도 대략적 범위 (south, north, west, east)
BB = {'서울': (37.41, 37.72, 126.76, 127.19), '경기': (36.9, 38.3, 126.35, 127.9), '인천': (37.2, 37.85, 126.0, 126.85),
      '세종': (36.43, 36.7, 127.1, 127.45), '대전': (36.2, 36.5, 127.2, 127.55), '충북': (36.0, 37.3, 127.3, 128.7),
      '충남': (35.9, 37.1, 125.9, 127.6), '강원': (37.0, 38.65, 127.05, 129.4), '부산': (34.95, 35.4, 128.75, 129.3),
      '대구': (35.6, 36.05, 128.3, 128.8), '울산': (35.35, 35.75, 129.0, 129.5), '경북': (35.55, 37.6, 128.0, 130.95),
      '경남': (34.55, 35.95, 127.55, 129.3), '광주': (34.95, 35.3, 126.6, 127.05), '전남': (34.2, 35.5, 126.0, 127.9),
      '전북': (35.3, 36.2, 126.4, 127.9), '제주': (33.1, 33.6, 126.1, 127.0)}
PROV = {'서울': '서울특별시', '경기': '경기도', '인천': '인천광역시', '세종': '세종특별자치시', '대전': '대전광역시', '충북': '충청북도',
        '충남': '충청남도', '강원': '강원특별자치도', '부산': '부산광역시', '대구': '대구광역시', '울산': '울산광역시', '경북': '경상북도',
        '경남': '경상남도', '광주': '광주광역시', '전남': '전라남도', '전북': '전북특별자치도', '제주': '제주특별자치도'}


def venue_query(v):
    """app.js venueQuery() 와 동일한 정리 규칙."""
    v = str(v or '')
    q = re.split(r'[(（]', v)[0]
    q = re.split(r'\s[·—–-]\s|·|—', q)[0]
    q = re.sub(r'\s*(일원|일대|집결|옆.*|[A-Z]구역)$', '', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q or v.strip()


def candidates(key, region):
    c = [key]
    k2 = re.sub(r'\s*(출발|출발점|도착|앞|인근|부근|일원)$', '', key).strip()
    if k2 != key: c.append(k2)
    c.append(PROV.get(region, region) + ' ' + k2)
    w = k2.split(' ')
    if len(w) > 1:
        c.append(' '.join(w[:2]))      # 앞 두 단어 (예: "경주 보덕동행정복지센터")
        c.append(w[0] + ' ' + w[-1])   # 첫 + 끝 단어
        c.append(w[-1])
    out, seen = [], set()
    for x in c:
        if x and x not in seen and len(x) >= 2: seen.add(x); out.append(x)
    return out


def nominatim(q):
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': q, 'format': 'json', 'countrycodes': 'kr', 'limit': 5, 'accept-language': 'ko'})
    r = urllib.request.Request(u, headers={'User-Agent': UA})
    with urllib.request.urlopen(r, timeout=30) as f:
        d = json.load(f)
    time.sleep(1.2)  # 초당 1회 이하
    return d


def plausible(key, cand, display):
    """전체 이름(또는 시·도 접두 + 전체 이름)으로 찾은 결과는 그대로 신뢰. 일부 단어만 쓴 후보는 '주차장' '광장' 같은
    흔한 이름이 엉뚱한 곳에 잡히기 쉬워서, 장소 이름의 첫 단어가 결과 주소에 들어 있을 때만 받는다."""
    k2 = re.sub(r'\s*(출발|출발점|도착|앞|인근|부근|일원)$', '', key).strip()
    if cand in (key, k2) or cand.endswith(' ' + k2): return True
    first = key.split(' ')[0]
    return len(first) >= 2 and first in display


def geocode(key, region):
    if region not in BB: return None
    s, n, w, e = BB[region]
    for i, c in enumerate(candidates(key, region)):
        for r in nominatim(c):
            la, lo = float(r['lat']), float(r['lon'])
            if not (s <= la <= n and w <= lo <= e): continue
            if region == '광주' and '광주' not in r.get('display_name', ''): continue
            if not plausible(key, c, r.get('display_name', '')): continue
            return {'lat': round(la, 5), 'lng': round(lo, 5), 'q': c, 'name': r.get('display_name', '')[:60]}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--retry', action='store_true'); ap.add_argument('--max', type=int, default=80)
    a = ap.parse_args()
    today = datetime.date.today().isoformat()
    races = json.load(open(RACES, encoding='utf8'))['races']
    cache = json.load(open(CACHE, encoding='utf8')) if os.path.exists(CACHE) else {}
    todo = {}
    for r in races:
        if (r.get('end_date') or r['date']) < today: continue
        v = r.get('venue') or ''
        if not v or '온라인' in v or r.get('region') not in BB: continue
        k = venue_query(v)
        if not k or k in todo: continue
        c = cache.get(k)
        if c and ('lat' in c or (not a.retry and c.get('fail', '') > (datetime.date.today() - datetime.timedelta(days=RETRY_DAYS)).isoformat())): continue
        todo[k] = r['region']
    print(f'새로 처리할 장소 {len(todo)}곳 (상한 {a.max})')
    ok = fail = 0
    for k, region in list(todo.items())[:a.max]:
        try:
            h = geocode(k, region)
        except Exception as ex:
            print('  오류(캐시 안 함):', k, ex); continue
        if h: cache[k] = h; ok += 1; print('  ✓', k, h['lat'], h['lng'], '|', h['name'])
        else: cache[k] = {'fail': today}; fail += 1; print('  ✗', k)
        tmp = CACHE + '.tmp'
        json.dump(dict(sorted(cache.items())), open(tmp, 'w', encoding='utf8'), ensure_ascii=False, indent=0)
        os.replace(tmp, CACHE)
    print(f'완료: 좌표 {ok} · 실패 {fail} · 캐시 총 {len(cache)}')


if __name__ == '__main__':
    main()
