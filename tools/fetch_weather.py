#!/usr/bin/env python3
"""대회 당일 날씨 예보 수집기 → data/weather.json

  python3 tools/fetch_weather.py            # 앞으로 열리는 모든 대회(국내 data/races.json + 해외 data/overseas.json)

- 표시 범위: 국내는 대회 10일 전부터, 해외는 14일 전부터. 더 먼 대회는 'pending'(표시 시작일)만 기록한다.
- 좌표: 국내 = data/venue_geo.json(장소 지오코딩 캐시) → 없으면 Open-Meteo 지오코딩(시·도 범위 안일 때만) → 그래도 없으면
  광역시(서울·부산·대구·인천·광주·대전·울산·세종)만 도시 중심 좌표(geo='city'). 그 외엔 날씨를 표시하지 않는다.
  해외 = GEO_OVERSEAS 표의 도시를 Open-Meteo 지오코딩으로 찾고 국가·주 일치를 확인한 값(data/weather_geo.json 캐시).
- 실패해도 빌드는 깨지지 않는다: 항상 exit 0, 요청이 실패한 대회는 이전 예보를 40시간까지만 유지한다.

[예보 소스 교체] PROVIDERS 에 함수를 하나 추가하고 ROUTES 의 'domestic' 값을 바꾸면 된다.
  provider 함수 규약: fn(lat, lng, date_iso, start_time) -> dict(cat, label, tmin, tmax, pop, wind, tstart) 또는 None
    cat   : sun / partly / cloud / fog / rain / snow / thunder (weather_lib.ICONS 의 키)
    wind  : m/s,  pop : %,  tstart : 출발 시각의 기온(모르면 None)
  예) 기상청 단기(3일)·중기예보로 바꿀 때: def kma(...) 를 만들고 PROVIDERS['kma']=kma, ROUTES['domestic']='kma'.
      (기상청은 격자/지역코드가 필요하므로 provider 안에서 변환한다. 10일 밖은 None 을 돌려주면 pending 으로 처리된다.)
"""
import datetime, json, os, re, sys, time, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
KST = ZoneInfo('Asia/Seoul')
NOW = datetime.datetime.now(KST)
TODAY = NOW.date()
UA = 'runwoori-site/1.0 (runwoori@gmail.com)'

HORIZON = {'domestic': 10, 'overseas': 14}          # 대회일 며칠 전부터 표시할지
ROUTES = {'domestic': 'open-meteo', 'overseas': 'open-meteo'}
STALE_HOURS = 40

# ── 해외 도시 → Open-Meteo 지오코딩 조건(검색어, 국가코드, 주/도 이름에 들어갈 글자) ──
GEO_OVERSEAS = {
    'tokyo': ('Tokyo', 'JP', 'Tokyo'), 'osaka': ('Osaka', 'JP', 'Osaka'), 'nagoya': ('Nagoya', 'JP', 'Aichi'),
    'fukuoka': ('Fukuoka', 'JP', 'Fukuoka'), 'kyoto': ('Kyoto', 'JP', 'Kyoto'), 'okinawa': ('Okinawa', 'JP', 'Okinawa'),
    'boston': ('Boston', 'US', 'Massachusetts'), 'chicago': ('Chicago', 'US', 'Illinois'), 'new-york': ('New York', 'US', 'New York'),
    'honolulu': ('Honolulu', 'US', 'Hawaii'), 'london': ('London', 'GB', 'England'), 'berlin': ('Berlin', 'DE', 'Berlin'),
    'paris': ('Paris', 'FR', 'le-de-France'), 'sydney': ('Sydney', 'AU', 'New South Wales'), 'gold-coast': ('Gold Coast', 'AU', 'Queensland'),
    'taipei': ('Taipei', 'TW', None), 'hong-kong': ('Hong Kong', 'HK', None),
    'kitakyushu': ('Kitakyushu', 'JP', 'Fukuoka'), 'kumamoto': ('Kumamoto', 'JP', 'Kumamoto'), 'kochi': ('Kochi', 'JP', 'Kochi'),
    'kagoshima': ('Kagoshima', 'JP', 'Kagoshima'), 'tokushima': ('Tokushima', 'JP', 'Tokushima'), 'nagano': ('Nagano', 'JP', 'Nagano'),
    'naha': ('Naha', 'JP', 'Okinawa'), 'barcelona': ('Barcelona', 'ES', 'Catalonia'), 'valencia': ('Valencia', 'ES', 'Valencia'),
}
# 광역시 중심(지오코딩 실패 시 도시 단위로만 표시). (검색어, 시·도 범위는 geocode_venues.BB 사용)
METRO = {'서울': 'Seoul', '부산': 'Busan', '대구': 'Daegu', '인천': 'Incheon', '광주': 'Gwangju', '대전': 'Daejeon', '울산': 'Ulsan', '세종': 'Sejong'}

WMO = {0: ('sun', '맑음'), 1: ('sun', '대체로 맑음'), 2: ('partly', '구름 조금'), 3: ('cloud', '흐림'), 45: ('fog', '안개'), 48: ('fog', '안개'),
       51: ('rain', '약한 이슬비'), 53: ('rain', '이슬비'), 55: ('rain', '강한 이슬비'), 56: ('rain', '어는 이슬비'), 57: ('rain', '어는 이슬비'),
       61: ('rain', '약한 비'), 63: ('rain', '비'), 65: ('rain', '강한 비'), 66: ('rain', '어는 비'), 67: ('rain', '어는 비'),
       71: ('snow', '약한 눈'), 73: ('snow', '눈'), 75: ('snow', '강한 눈'), 77: ('snow', '진눈깨비'),
       80: ('rain', '약한 소나기'), 81: ('rain', '소나기'), 82: ('rain', '강한 소나기'), 85: ('snow', '눈 소나기'), 86: ('snow', '강한 눈 소나기'),
       95: ('thunder', '뇌우'), 96: ('thunder', '뇌우(우박)'), 99: ('thunder', '뇌우(우박)')}


def http_json(url, tries=3, timeout=20):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            last = e; time.sleep(1.5 * (i + 1))
    raise last


# ── provider: Open-Meteo (키 불필요, 최대 16일) ──
def open_meteo(lat, lng, date_iso, start_time):
    q = urllib.parse.urlencode({
        'latitude': f'{lat:.4f}', 'longitude': f'{lng:.4f}', 'timezone': 'auto', 'start_date': date_iso, 'end_date': date_iso,
        'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max',
        'hourly': 'temperature_2m', 'wind_speed_unit': 'ms', 'temperature_unit': 'celsius'})
    j = http_json('https://api.open-meteo.com/v1/forecast?' + q)
    dd = j['daily']
    if dd['time'][0] != date_iso: return None
    tmin, tmax, code = dd['temperature_2m_min'][0], dd['temperature_2m_max'][0], dd['weather_code'][0]
    if tmin is None or tmax is None or code is None: return None
    cat, label = WMO.get(int(code), ('cloud', '흐림'))
    # 약한 이슬비(51)인데 강수확률이 20% 미만이면 '약한 이슬비'가 과장이라 '흐림'으로 표시(수치는 그대로)
    if int(code) == 51 and (dd.get('precipitation_probability_max') or [100])[0] < 20: cat, label = 'cloud', '흐림'
    tstart = None
    if start_time and re.match(r'^\d\d:\d\d$', start_time):
        h = int(start_time[:2])
        try:
            v = j['hourly']['temperature_2m'][h]
            tstart = None if v is None else round(v, 1)
        except Exception: pass
    pop = (dd.get('precipitation_probability_max') or [None])[0]
    wind = (dd.get('wind_speed_10m_max') or [None])[0]
    return dict(cat=cat, label=label, tmin=round(tmin, 1), tmax=round(tmax, 1), pop=pop, wind=wind, tstart=tstart)


PROVIDERS = {'open-meteo': open_meteo}
SOURCE_NAME = {'open-meteo': 'Open-Meteo'}
# 'kma': 기상청 단기·중기예보 — 아직 없음. 위 규약대로 함수를 만들어 PROVIDERS/SOURCE_NAME/ROUTES 에 등록하면 된다.


# ── 지오코딩 ──
GEO_CACHE_P = os.path.join(ROOT, 'data', 'weather_geo.json')


def load_json(p, default):
    try: return json.load(open(p, encoding='utf8'))
    except Exception: return default


def save_json(p, o):
    tmp = p + '.tmp'
    json.dump(o, open(tmp, 'w', encoding='utf8'), ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, p)


def om_geocode(name, cc, admin_hint=None, lang='en'):
    u = 'https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode({'name': name, 'count': 10, 'language': lang, 'countryCode': cc})
    res = (http_json(u).get('results') or [])
    if admin_hint:
        res = [x for x in res if admin_hint.lower() in (x.get('admin1') or '').lower()]
    res = [x for x in res if x.get('feature_code', '').startswith('PPL')]
    if not res: return None
    res.sort(key=lambda x: -(x.get('population') or 0))
    h = res[0]
    return {'lat': h['latitude'], 'lng': h['longitude'], 'name': f"{h['name']}, {h.get('admin1', '')}, {h['country_code']}"}


def domestic_geo(r, venue_geo, geo_cache, BB, venue_query):
    """(lat,lng,geo) 또는 None. 확실하지 않으면 None."""
    v = r.get('venue') or ''
    region = r.get('region')
    if not v or region not in BB or region == '전국': return None
    # 온라인·버추얼(장소 없음)·취소된 대회는 날씨를 표시하지 않는다
    if re.search(r'온라인|버추얼|virtual|어디서나|비대면|취소|미정', v + ' ' + (r.get('name') or '') + ' ' + (r.get('category') or ''), re.I): return None
    k = venue_query(v)
    g = venue_geo.get(k)
    s, n, w, e = BB[region]
    if g and 'lat' in g and s <= g['lat'] <= n and w <= g['lng'] <= e:
        return g['lat'], g['lng'], 'venue'
    # 장소 좌표가 없으면 광역시만 도시 중심으로 (지오코딩 캐시)
    if region in METRO:
        key = 'metro:' + region
        c = geo_cache.get(key)
        if c is None:
            try:
                c = om_geocode(METRO[region], 'KR', None) or {'fail': TODAY.isoformat()}
            except Exception:
                return None
            if 'lat' in c and not (s <= c['lat'] <= n and w <= c['lng'] <= e): c = {'fail': TODAY.isoformat()}
            geo_cache[key] = c
        if 'lat' in c: return c['lat'], c['lng'], 'city'
    return None


def overseas_geo(slug, geo_cache):
    spec = GEO_OVERSEAS.get(slug)
    if not spec: return None
    key = 'ov:' + slug
    c = geo_cache.get(key)
    if c is None:
        try:
            c = om_geocode(*spec) or {'fail': TODAY.isoformat()}
        except Exception:
            return None
        geo_cache[key] = c
    return (c['lat'], c['lng'], 'city') if 'lat' in c else None


def main():
    from geocode_venues import BB
    from build_race_pages import venue_query
    out_p = os.path.join(ROOT, 'data', 'weather.json')
    prev = load_json(out_p, {}).get('items', {})
    venue_geo = load_json(os.path.join(ROOT, 'data', 'venue_geo.json'), {})
    geo_cache = load_json(GEO_CACHE_P, {})
    races = load_json(os.path.join(ROOT, 'data', 'races.json'), {}).get('races', [])
    ov = load_json(os.path.join(ROOT, 'data', 'overseas.json'), {}).get('races', [])

    targets = []   # (id, kind, date, start_time, lat, lng, geo)
    stat = {'no_coords': 0, 'no_coords_ids': [], 'past_or_ongoing': 0}
    for r in races:
        d = r['date']
        if d < TODAY.isoformat(): stat['past_or_ongoing'] += 1; continue
        g = domestic_geo(r, venue_geo, geo_cache, BB, venue_query)
        if not g: stat['no_coords'] += 1; stat['no_coords_ids'].append(r['id']); continue
        targets.append((r['id'], 'domestic', d, r.get('start_time'), *g))
    for r in ov:
        d = r['date']
        if d < TODAY.isoformat(): stat['past_or_ongoing'] += 1; continue
        g = overseas_geo(r['slug'], geo_cache)
        if not g: stat['no_coords'] += 1; stat['no_coords_ids'].append(r['id']); continue
        targets.append((r['id'], 'overseas', d, r.get('start_time'), *g))
    save_json(GEO_CACHE_P, geo_cache)

    items, pending, fails, cache, attempted = {}, {}, 0, {}, 0
    for rid, kind, d, st, lat, lng, geo in targets:
        race_d = datetime.date.fromisoformat(d)
        days = (race_d - TODAY).days
        show_from = race_d - datetime.timedelta(days=HORIZON[kind])
        if days > HORIZON[kind]:
            pending[rid] = {'date': d, 'show_from': show_from.isoformat(), 'geo': geo}
            continue
        prov = ROUTES[kind]; attempted += 1
        ck = (prov, round(lat, 2), round(lng, 2), d, st)
        try:
            if ck not in cache: cache[ck] = PROVIDERS[prov](lat, lng, d, st)
            w = cache[ck]
        except Exception as e:
            print('  예보 실패', rid, d, repr(e)[:120]); fails += 1
            o = prev.get(rid)
            if o:   # 이전 값은 40시간까지만 유지(날짜가 지났거나 오래되면 버린다)
                try:
                    if o['date'] == d and NOW - datetime.datetime.fromisoformat(o['fetched']) <= datetime.timedelta(hours=STALE_HOURS): items[rid] = o
                except Exception: pass
            continue
        if not w:
            pending[rid] = {'date': d, 'show_from': TODAY.isoformat(), 'geo': geo, 'unavailable': True}; continue
        items[rid] = {**w, 'date': d, 'start_time': st if (st and re.match(r'^\d\d:\d\d$', st)) else None, 'provider': prov,
                      'source': SOURCE_NAME[prov], 'geo': geo, 'fetched': NOW.isoformat(timespec='seconds')}
        time.sleep(0.15)
    # 예보가 안 오는 날짜(unavailable)는 표시 시작일 안내를 쓰지 않는다
    pending = {k: v for k, v in pending.items() if not v.get('unavailable')}
    if attempted and fails == attempted and prev:
        print('모든 요청이 실패 — 이전 파일 유지'); return
    out = {'schema': 1, 'updated': NOW.isoformat(timespec='seconds'), 'horizon_days': HORIZON, 'routes': ROUTES,
           'items': items, 'pending': pending,
           'stats': {'forecast': len(items), 'pending': len(pending), 'no_coords': stat['no_coords'], 'failed_requests': fails}}
    save_json(out_p, out)
    print(f'날씨: 예보 {len(items)}개 · 표시 시작 전 {len(pending)}개 · 좌표 없음 {stat["no_coords"]}개 · 요청 실패 {fails}개')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:      # 어떤 경우에도 빌드를 막지 않는다
        print('날씨 수집 중 오류(무시하고 계속):', repr(e)[:200])
    sys.exit(0)
