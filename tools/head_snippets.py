"""AdSense / GA4 `<head>` snippets shared by the page generators.

Home, calculators, and other thin utility screens are listed in AD_FREE.
They must not load adsbygoogle.js. Race, overseas, and landing generators
copy the AdSense block from a content page (about.html), not from index.html,
so removing the script from the home page does not turn ads off on race pages.

GA4 still follows index.html.
"""
import os
import re

# 본문이 얇거나 도구·개인 화면이라 광고 스크립트를 넣지 않는 파일.
# tools/set_adsense.sh 가 이 목록은 다시 켜지 않는다.
AD_FREE = frozenset({
    'index.html',   # / 대회 달력. 목록은 app.js 가 채운다
    'home.html',    # my.html 로 보내는 리다이렉트
    'races.html',   # index.html 로 보내는 리다이렉트
    'race.html',    # race/<id>.html 로 보내는 리다이렉트
    'my.html',      # 나의 레이스
    'tools.html',   # 훈련 계획·페이스 계산기
    'plan.html',    # 훈련 플랜
    'records.html', # 기록 관리
    'pro.html',     # 프로 미리보기
    'saved.html',   # 저장한 대회·코스
    'install.html',
    'offline.html',
    '404.html',
})

_ADS = re.compile(r'<!--ADSENSE:START-->.*?<!--ADSENSE:END-->', re.S)
_GA4 = re.compile(r'<!--GA4:START-->.*?<!--GA4:END-->', re.S)
_ADS_NOTE = re.compile(r'^[ \t]*<!-- Google AdSense:[^>]*-->\n', re.M)


def strip_adsense(html):
    """Remove the AdSense loader block and the note above it. Leave GA4."""
    html = _ADS_NOTE.sub('', html)
    html = re.sub(r'<!--ADSENSE:START-->.*?<!--ADSENSE:END-->\n?', '', html, flags=re.S)
    return html


def _read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except OSError:
        return ''


def adsense_block(root):
    """Live AdSense snippet from a content page. Never from an AD_FREE screen."""
    m = _ADS.search(_read(os.path.join(root, 'about.html')))
    if m:
        return m.group(0)
    for name in sorted(os.listdir(root)):
        if not name.endswith('.html') or name in AD_FREE:
            continue
        m = _ADS.search(_read(os.path.join(root, name)))
        if m:
            return m.group(0)
    return ''


def ga4_block(root):
    m = _GA4.search(_read(os.path.join(root, 'index.html')))
    return m.group(0) if m else ''


def adsense_and_ga4(root):
    ads = adsense_block(root)
    ga = ga4_block(root)
    if ads and ga:
        return ads + '\n' + ga
    return ads or ga
