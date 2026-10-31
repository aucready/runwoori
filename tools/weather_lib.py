"""대회 날씨 예보 표시용 공통 코드 (정적 페이지 생성기에서 import).

- 데이터: data/weather.json (tools/fetch_weather.py 가 매일 만든다). 없거나 깨져 있으면 날씨 없이 그대로 빌드된다.
- 이 파일은 '표시'만 맡는다. 예보를 어디서 가져오는지는 fetch_weather.py 의 PROVIDERS/ROUTES 에서 바꾼다.
- 아이콘은 선 아이콘(stroke) 한 벌. 모든 예보 소스는 같은 cat(sun/partly/cloud/fog/rain/snow/thunder)로 맞춰서 넘긴다.
"""
import json, os, html, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
KST = ZoneInfo('Asia/Seoul')
WD = ['월', '화', '수', '목', '금', '토', '일']
STALE_HOURS = 40        # 이보다 오래된 예보는 숨긴다(수집이 며칠째 실패한 경우)

_CLOUD = 'M7.5 17.5h9a3.75 3.75 0 0 0 .5-7.46 5.25 5.25 0 0 0-10.1 1.2A3.15 3.15 0 0 0 7.5 17.5z'
_SUN_RAYS = 'M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4'
ICONS = {
    'sun': f'<circle cx="12" cy="12" r="4"/><path d="{_SUN_RAYS}"/>',
    'partly': f'<path d="M9 3.5v1.6M3.6 6.2l1.2 1M2.5 11.5h1.6M14.6 6.2l-1.2 1"/><path d="M6.2 11.5a3.3 3.3 0 0 1 6.2-1.6"/><path transform="translate(2.5 2)" d="{_CLOUD}"/>',
    'cloud': f'<path d="{_CLOUD}"/>',
    'fog': '<path d="M5 8.5h14M3.5 12.5h17M6 16.5h12M9 20.5h6"/>',
    'rain': f'<path transform="translate(0 -3)" d="{_CLOUD}"/><path d="M8.5 17.5l-1 3M12.5 17.5l-1 3M16.5 17.5l-1 3"/>',
    'snow': f'<path transform="translate(0 -3)" d="{_CLOUD}"/><path d="M8.5 18v3M7 19.5h3M15.5 18v3M14 19.5h3"/>',
    'thunder': f'<path transform="translate(0 -3)" d="{_CLOUD}"/><path d="M12.8 15.5l-2.3 3h3l-2.3 3"/>',
}


def icon(cat, size=20):
    p = ICONS.get(cat) or ICONS['cloud']
    return (f'<svg class="wx-ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{p}</svg>')


def esc(s): return html.escape(str(s), quote=True)
def _pd(s): y, m, d = map(int, s.split('-')); return datetime.date(y, m, d)
def _deg(n): return f'{int(round(n))}°'.replace('-0°', '0°')


def load(path=None):
    """data/weather.json 을 읽어 {'items':..,'pending':..} 로. 실패하면 빈 값."""
    p = path or os.path.join(ROOT, 'data', 'weather.json')
    try:
        d = json.load(open(p, encoding='utf8'))
        return {'items': d.get('items') or {}, 'pending': d.get('pending') or {}}
    except Exception:
        return {'items': {}, 'pending': {}}


def _fresh(it, now):
    try:
        f = datetime.datetime.fromisoformat(it['fetched'])
        return (now - f) <= datetime.timedelta(hours=STALE_HOURS)
    except Exception:
        return False


def get(W, rid, today):
    """표시할 예보(지난 대회·오래된 예보는 None)."""
    it = (W.get('items') or {}).get(rid)
    if not it: return None
    if _pd(it['date']) < today: return None
    if not _fresh(it, datetime.datetime.now(KST)): return None
    return it


def chip(W, rid, today):
    """목록/카드용: 아이콘 + 기온만."""
    it = get(W, rid, today)
    if not it: return ''
    t = f'{_deg(it["tmin"])}~{_deg(it["tmax"])}'
    tip = f'대회 당일 예보 · {it["label"]} · 최저 {_deg(it["tmin"])} 최고 {_deg(it["tmax"])}'
    return (f'<span class="ed-wx" title="{esc(tip)}" aria-label="{esc(tip)}">{icon(it["cat"], 15)}'
            f'<span class="ed-wx-t">{t}</span></span>')


def panel(W, rid, today, indent=''):
    """상세 페이지용 블록. 예보가 있으면 예보, 아직 멀면 '표시 시작일' 안내, 좌표가 불확실하면 빈 문자열."""
    it = get(W, rid, today)
    if it:
        d = _pd(it['date'])
        cells = [('기온', f'{_deg(it["tmin"])}<i>/</i>{_deg(it["tmax"])}')]
        if it.get('tstart') is not None and it.get('start_time'):
            cells.append((f'출발 {esc(it["start_time"])}', _deg(it['tstart'])))
        cells.append(('강수확률', f'{int(round(it["pop"]))}<small>%</small>' if it.get('pop') is not None else '—'))
        cells.append(('바람', f'{int(round(it["wind"]))}<small>m/s</small>' if it.get('wind') is not None else '—'))
        try:
            f = datetime.datetime.fromisoformat(it['fetched']).astimezone(KST)
            upd = f'{f.month}.{f.day} {f.hour:02d}:{f.minute:02d} 갱신'
        except Exception:
            upd = ''
        geo = ' · 도시 중심 기준' if it.get('geo') == 'city' else ''
        grid = ''.join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in cells)
        return (f'<section class="ed-wx-panel" aria-label="대회 당일 날씨 예보">'
                f'<div class="ed-wx-head"><span class="ed-wx-ic">{icon(it["cat"], 30)}</span>'
                f'<div><p class="ed-wx-k">대회 당일 날씨 예보</p><p class="ed-wx-c">{esc(it["label"])}<span> · {d.month}.{d.day}({WD[d.weekday()]})</span></p></div></div>'
                f'<dl class="ed-wx-grid">{grid}</dl>'
                f'<p class="ed-wx-src">{esc(it.get("source", "Open-Meteo"))} 예보 기준{" · " + upd if upd else ""}{geo} · 예보는 바뀔 수 있어요</p></section>')
    pend = (W.get('pending') or {}).get(rid)
    if pend:
        d = _pd(pend['show_from'])
        if d > today:
            return (f'<section class="ed-wx-panel later" aria-label="대회 당일 날씨 예보"><p class="ed-wx-later">'
                    f'<span class="ed-wx-k">대회 당일 날씨</span> 예보는 {d.month}월 {d.day}일부터 표시돼요</p></section>')
    return ''
