#!/usr/bin/env python3
"""정적 HTML 메뉴·푸터 넣기 (SEO P0, 2026-11-22).

  python3 tools/static_nav.py          # 루트 *.html + race/ month/ region/ overseas/ guide/ 전부

- app.js 의 layout() 이 그리는 상단 메뉴·푸터·하단 탭바와 같은 마크업·같은 항목을 정적 HTML 로 미리 넣는다.
  구글이 JS 를 돌리지 않아도 주 메뉴 링크(대회 달력·해외·가이드·코스·훈련·러닝 약속 잡기 …)를 따라갈 수 있게.
- 각 요소에 data-rw-static 을 달아 두고, layout() 이 돌면 먼저 이것들을 지운 뒤 기존 JS 메뉴를 넣는다
  → JS 가 돌면 지금과 똑같이 보이고 중복 표시가 없다. 같은 자리·같은 높이라 레이아웃 이동도 없다.
- 표시는 <!--RWNAV:HEAD-->…<!--/RWNAV:HEAD-->, <!--RWNAV:FOOT-->…<!--/RWNAV:FOOT--> 사이. 다시 돌려도 한 번만 들어간다.
- layout() 을 부르지 않는 리다이렉트 화면(home·races·offline)과 crew/ 는 건드리지 않는다.
- tools/daily_publish.sh 가 모든 생성기 다음, sitemap 전에 실행한다.
"""
import glob, hashlib, json, os, re, sys, datetime
from zoneinfo import ZoneInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
KST = ZoneInfo('Asia/Seoul')
EN = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']   # date.weekday() 기준
SITE_NAME = 'Run우리'
# app.js layout() 의 nav / bottom 과 같은 항목·같은 순서 (바꿀 때는 두 곳을 같이)
NAV = [('/', '대회 달력', 'races'), ('/overseas.html', '해외 대회', 'overseas'), ('/my.html', '나의 레이스', 'home'), ('/blog.html', '러닝 가이드', 'blog'),
       ('/courses.html', '러닝 코스', 'courses'), ('/tools.html', '훈련 · 페이스', 'tools'), ('/crew/', '러닝 약속 잡기', 'crew'), ('/saved.html', '저장', 'saved')]
BOTTOM = [('/', '대회', 'races'), ('/my.html', '나의 레이스', 'home'), ('/blog.html', '가이드', 'blog'), ('/saved.html', '저장', 'saved')]
SUBDIRS = ('race', 'month', 'region', 'overseas', 'guide', 'marathon-schedule', 'distance', 'tools')   # tools/ 는 *.html(페이스 계산기)만
SKIP = {'home.html', 'races.html', 'offline.html'}
# 푸터 '대회 모아보기' — app.js FOOT_HUBS 와 같은 항목·순서 (SEO P1)
FOOT_HUBS = [('/marathon-schedule/2026.html', '2026 마라톤 일정'), ('/marathon-schedule/2027.html', '2027 마라톤 일정'), ('/open.html', '접수 중인 대회'), ('/distance/half.html', '하프'),
             ('/distance/10k.html', '10km'), ('/distance/5k.html', '5km'), ('/distance/full.html', '풀코스'), ('/tools/pace-calculator.html', '페이스 계산기')]
H0, H1, F0, F1 = '<!--RWNAV:HEAD-->', '<!--/RWNAV:HEAD-->', '<!--RWNAV:FOOT-->', '<!--/RWNAV:FOOT-->'


def asset_ver():
    """app.js·site.css 내용 해시. 서비스 워커(sw.js)가 정적 파일을 stale-while-revalidate 로 주기 때문에
    주소에 ?v= 를 붙여야 새 app.js(정적 메뉴를 지우는 코드)가 바로 쓰인다 — 옛 app.js 와 정적 메뉴가 겹쳐 보이는 일을 막는다."""
    h = hashlib.sha1()
    for f in ('app.js', 'site.css'):
        h.update(open(os.path.join(ROOT, f), 'rb').read())
    return h.hexdigest()[:8]


def updated_text():
    try:
        fa = json.load(open(os.path.join(ROOT, 'data', 'races.json'), encoding='utf8')).get('fetched_at') or ''
    except Exception:
        fa = ''
    m = re.match(r'(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)', fa)
    return f'마지막 업데이트 {m[2]}.{m[3]} {m[4]}:{m[5]}' if m else '데이터 불러오는 중'


def _a(href, label, key, active, badge=True):
    on = key == active
    b = '<span class="n" data-saved-count hidden>0</span>' if badge and key == 'saved' else ''
    return f'<a href="{href}" class="{"is-on" if on else ""}" {"aria-current=\"page\"" if on else ""}>{label}{b}</a>'


def head_html(active, path, upd):
    t = datetime.datetime.now(KST).date()
    links = (f'<a class="ed-link {"is-on" if active == "courses" else ""}" href="/courses.html">코스</a>'
             f'<a class="ed-link {"is-on" if active == "tools" else ""}" href="/tools.html">훈련</a>'
             f'<a class="ed-link {"is-on" if active == "crew" else ""}" href="/crew/">약속 잡기</a>')
    return (f'{H0}<a class="skip-link" data-rw-static href="/{path}#main">본문으로 건너뛰기</a><header class="ed-mast" data-rw-static><div class="ed-wrap"><div class="ed-mast-top">'
            f'<span class="ed-label">{t.year}.{t.month:02d}.{t.day:02d} {EN[t.weekday()]}</span><span class="ed-label">{upd}</span></div>'
            f'<div class="ed-mast-row"><a class="ed-wordmark" href="/" aria-label="{SITE_NAME} 홈"><img src="/assets/logo/runwoori-wordmark-light-small.svg" alt="{SITE_NAME}" width="118" height="28"></a>'
            f'<nav class="ed-mast-nav" aria-label="주 메뉴">{"".join(_a(h, l, k, active) for h, l, k in NAV)}</nav>'
            f'<div class="ed-mast-links">{links}</div></div></div></header>{H1}')


def foot_html(active, upd):
    tab = ''.join(_a(h, l, k, 'races' if active == 'overseas' and k == 'races' else active) for h, l, k in BOTTOM)
    return (f'{F0}<footer class="ed-footer" data-rw-static><div class="ed-wrap"><div class="ed-rule" style="border-color:var(--ink)"></div><p class="ed-small" style="padding-top:14px">'
            f'<img class="ed-foot-logo" src="/assets/logo/runwoori-wordmark-light-small.svg" alt="{SITE_NAME}" width="101" height="24"><br>'
            f'{SITE_NAME}는 개인 프로젝트입니다. 대회 일정은 <a href="https://www.kormarathon.com" rel="noopener" target="_blank">KorMarathon</a>의 공개 정보를 하루 한 번 수집하고, '
            f'주요 대회는 공식 홈페이지로 직접 확인해 정리합니다. 일정·참가비·접수 기간은 바뀔 수 있으니 신청 전 반드시 공식 홈페이지에서 확인하세요.<br><span>{upd}</span></p>'
            f'<nav class="ed-foot-links ed-foot-hubs" aria-label="대회 모아보기">{"".join(f'<a href="{h}">{l}</a>' for h, l in FOOT_HUBS)}</nav>'
            f'<nav class="ed-foot-links" aria-label="사이트 정보"><a href="/crew/">러닝 약속 잡기</a><a href="/about.html">사이트 소개</a><a href="/privacy.html">개인정보처리방침</a>'
            f'<a href="/install.html">앱으로 설치</a><a href="/terms.html">이용약관</a><a href="/contact.html">문의하기</a></nav></div></footer>'
            f'<nav class="ed-tabbar" data-rw-static aria-label="하단 메뉴">{tab}</nav>{F1}')


_LAYOUT = re.compile(r"<script>[^<]*?layout\('([a-z]*)'\)", re.S)


def apply_file(p, upd, ver=''):
    rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
    s = open(p, encoding='utf8').read()
    s0 = s
    s = re.sub(re.escape(H0) + '.*?' + re.escape(H1), '', s, flags=re.S)
    s = re.sub(re.escape(F0) + '.*?' + re.escape(F1), '', s, flags=re.S)
    m = _LAYOUT.search(s)
    if not m or 'location.replace' in s[m.end():m.end() + 300] or '</main>' not in s:
        if s != s0: open(p, 'w', encoding='utf8').write(s)
        return False
    active = m.group(1)
    if ver:
        s = re.sub(r'(src|href)="(/?)(app\.js|site\.css)(\?v=\w+)?"', lambda x: f'{x.group(1)}="{x.group(2)}{x.group(3)}?v={ver}"', s)
    path = '' if rel == 'index.html' else rel
    s = re.sub(r'<body>', '<body class="ed-root">', s, count=1)
    s = re.sub(r'(<body[^>]*>)', lambda b: b.group(1) + head_html(active, path, upd), s, count=1)
    i = s.rfind('</main>') + len('</main>')
    s = s[:i] + foot_html(active, upd) + s[i:]
    if s != s0: open(p, 'w', encoding='utf8').write(s)
    return True


def main():
    upd = updated_text(); ver = asset_ver()
    files = [f for f in glob.glob(os.path.join(ROOT, '*.html')) if os.path.basename(f) not in SKIP]
    for d in SUBDIRS: files += glob.glob(os.path.join(ROOT, d, '*.html'))
    n = sum(apply_file(f, upd, ver) for f in sorted(files))
    print(f'static nav: {n}/{len(files)} pages (asset v={ver})')


if __name__ == '__main__': main()
