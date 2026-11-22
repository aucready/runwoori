#!/usr/bin/env python3
"""러닝 페이스 계산기 정적 페이지 (SEO P1, 2026-11-22).

  python3 tools/build_pace.py      # → tools/pace-calculator.html (주소 /tools/pace-calculator.html)

- 페이스표(4:00~8:00/km, 15초 간격 × 5K·10K·하프·풀)는 '기록 = 페이스 × 거리' 계산값이라 지어낸 수치가 없다.
- 위쪽 계산기는 tools.html 과 같은 app.js paceCalcHtml()/initPace() 를 쓴다.
- 도구 화면이라 광고(AdSense)는 넣지 않는다(head_snippets.AD_FREE). GA4 만 index.html 을 따른다.
"""
import os, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_overseas as bo
import head_snippets

ROOT = bo.ROOT; SITE = bo.SITE
esc = bo.esc
D = [('5K', 5.0), ('10K', 10.0), ('하프', 21.0975), ('풀코스', 42.195)]


def hms(s):
    s = round(s); h, m, x = s // 3600, s % 3600 // 60, s % 60
    return f'{h}:{m:02d}:{x:02d}' if h else f'{m}:{x:02d}'


def main():
    url = f'{SITE}/tools/pace-calculator.html'
    title = '러닝 페이스 계산기 — km당 페이스·완주 시간·5K~풀코스 페이스표 | Run우리'
    desc = '거리와 시간을 넣으면 km당 페이스를, 페이스를 넣으면 5km·10km·하프·풀코스 완주 시간을 계산해요. 자주 쓰는 페이스별 완주 시간표도 정리했어요.'
    rows = ''
    for sec in range(240, 481, 15):
        rows += (f'<tr><th scope="row">{sec // 60}\'{sec % 60:02d}"<span class="lp-kmh">시속 {3600 / sec:.1f}km</span></th><td class="lp-kmh-col">{3600 / sec:.1f}</td>' + ''.join(f'<td>{hms(sec * km)}</td>' for _, km in D) + '</tr>')
    ld = {'@context': 'https://schema.org', '@type': 'WebApplication', 'name': '러닝 페이스 계산기', 'url': url, 'applicationCategory': 'SportsApplication', 'operatingSystem': 'Any',
          'inLanguage': 'ko-KR', 'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'KRW'}}
    crumb = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': '훈련 · 페이스', 'item': SITE + '/tools.html'}, {'@type': 'ListItem', 'position': 2, 'name': '페이스 계산기', 'item': url}]}
    ld_html = f'<script type="application/ld+json">{bo.js(ld)}</script>\n<script type="application/ld+json">{bo.js(crumb)}</script>'
    head = bo.HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, adsense=head_snippets.ga4_block(ROOT), ld=ld_html)
    head = head.replace('property="og:type" content="article"', 'property="og:type" content="website"')
    th = ''.join(f'<th scope="col">{n}</th>' for n, _ in D)
    body = f'''<main class="ed-wrap" id="main"><div id="view">
<div style="padding:20px var(--page-x) 0"><nav class="ed-crumbs" aria-label="현재 위치"><a href="tools.html">훈련 · 페이스</a><span aria-hidden="true">›</span><span aria-current="page">페이스 계산기</span></nav></div>
<div class="landing-title"><h1 class="ed-h1">러닝 페이스 계산기</h1></div>
<p class="ed-lede lp-lede">목표 기록을 넣으면 1km 평균 페이스를, 페이스를 넣으면 완주 기록을 계산해요. 아래 표는 자주 쓰는 페이스(1km 4분~8분, 15초 간격)로 5K·10K·하프·풀코스를 달렸을 때의 완주 시간이에요.</p>
<section class="ed-section" style="margin-top:28px"><div class="ed-section-head major"><span class="no">01</span><h2 class="ed-h2">페이스 · 기록 계산</h2></div><div id="paceBox" style="min-height:420px"></div></section>
<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">02</span><h2 class="ed-h2">페이스별 완주 시간표</h2></div>
<p class="ed-body lp-p">완주 시간 = 1km 페이스 × 거리로 계산했어요(하프 21.0975km, 풀코스 42.195km). 같은 페이스를 끝까지 유지했을 때의 값이라, 급수·오르막·화장실 같은 변수는 들어 있지 않아요.</p>
<div class="lp-tablewrap"><table class="ed-table lp-pace"><thead><tr><th scope="col">1km 페이스</th><th scope="col" class="lp-kmh-col">시속(km)</th>{th}</tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="ed-section" style="margin-top:36px"><div class="ed-section-head"><span class="no">03</span><h2 class="ed-h2">이렇게 쓰세요</h2></div>
<dl class="ed-dl ov-dl ov-ways"><dt>페이스</dt><dd>1km를 달리는 데 걸리는 시간이에요. 5'30"는 1km를 5분 30초에 달린다는 뜻이고, 페이스가 작을수록 빨라요.</dd>
<dt>목표 기록 → 페이스</dt><dd>목표 기록(초) ÷ 거리(km)가 평균 페이스예요. 예를 들어 10km를 1시간에 달리려면 1km 6'00"를 유지하면 돼요.</dd>
<dt>다른 거리 예상 기록</dt><dd>위 계산기의 예상 기록은 리겔 공식으로 낸 단순 추정이에요. 훈련 상태나 코스에 따라 실제 기록과 다를 수 있어요.</dd></dl>
<ul class="ed-small" style="line-height:2;margin:14px var(--page-x) 0 18px;padding:0"><li><a class="ed-link" href="tools.html">대회 날짜로 주간 훈련표 만들기</a></li><li><a class="ed-link" href="guide/understanding-pace.html">페이스 이해하기</a></li><li><a class="ed-link" href="guide/race-pace-strategy.html">대회 페이스 전략</a></li>
<li><a class="ed-link" href="distance/10k.html">10km 대회 일정</a></li><li><a class="ed-link" href="distance/half.html">하프 마라톤 대회 일정</a></li></ul></section>
</div></main>
<script>layout('tools');
(function(){{ const box=$('#paceBox'); box.innerHTML=paceCalcHtml({{mode:true,splits:true}}); initPace(box); }})();
</script></body></html>
'''
    os.makedirs(os.path.join(ROOT, 'tools'), exist_ok=True)
    open(os.path.join(ROOT, 'tools', 'pace-calculator.html'), 'w', encoding='utf8').write(head + body)
    print('pace calculator: tools/pace-calculator.html (페이스', len(range(240, 481, 15)), '행)')


if __name__ == '__main__': main()
