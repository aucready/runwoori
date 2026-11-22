#!/usr/bin/env python3
"""SEO P3 미리보기: 러닝 의류·장비 가이드 5편 + 허브. 공식 자료 인용, 착화감 금지."""
from __future__ import annotations
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from build_shoes import page, disclosure, SITE, CHECKED_LABEL, esc, load as load_shoes

GUIDES = [
    ('temperature', '기온별 러닝 복장', '겹쳐 입기 구간을 공식 가이드와 한국 대회 월별로 연결했어요.'),
    ('winter', '겨울 러닝복', '추운 달 대회를 앞두고 레이어링·말단 보온의 공식 안내를 정리했어요.'),
    ('race-day', '대회 당일 복장·준비물', '거리와 예상 기온에 따라 무엇을 미리 정해 두면 좋은지 정리했어요.'),
    ('gloves', '러닝 장갑 고르는 기준', '방풍·터치스크린 등 고를 때 보는 항목만 적었어요. 특정 착화감은 짓지 않습니다.'),
    ('jacket', '러닝 바람막이', '바람·비에 대비할 때 공식 설명이 있는 항목만 안내해요.'),
]


def body_wrap(aff, label, title, lede, inner):
    return (f'{disclosure(aff)}<header class="ed-page-head" style="padding:18px var(--page-x) 0">'
            f'<div class="ed-label">{esc(label)}</div>'
            f'<h1 class="ed-h1" style="margin:12px 0 10px">{esc(title)}</h1>'
            f'<p class="ed-lede">{lede}</p></header>'
            f'<div class="ed-prose" style="padding:8px var(--page-x) 24px">{inner}</div>')


def temperature(aff):
    lede = (f'기온이 바뀌면 무엇을 입을지 헷갈리기 쉬워요. 나이키 코리아 공식 가이드는 약 15.6℃ 이상, 4.4~15.6℃, 4.4℃ 이하로 구간을 나눕니다. '
            f'아래는 그 구간을 그대로 옮기지 않고, 출처를 밝힌 뒤 한국 대회 달과 연결한 안내예요. 확인일 {CHECKED_LABEL}.')
    inner = f'''
<p>이 글은 복장 ‘추천 랭킹’이 아니에요. 소재 감촉이나 특정 상품의 따뜻함을 지어내지 않았고, 공식 가이드에 없는 온도 숫자는 만들지 않았습니다.</p>
<p>참고한 공식 자료: 나이키 코리아 <a class="ed-link" href="https://www.nike.com/kr/a/what-to-wear-by-temperature" rel="noopener noreferrer" target="_blank">기온에 적합한 러닝 복장 추천</a>(페이지 표기 마지막 업데이트 2025-07-11). 공식 글은 바깥 기온보다 약 5.6~11.1℃ 더 따뜻하게 입으라는 안내도 함께 적습니다. 체감은 바람·습도·개인 차에 따라 달라져요.</p>
<div class="sg-layer">
<article id="warm"><h3>약 15.6℃ 이상</h3><p class="deg">공식 가이드의 더운 날 구간</p>
<p>공식 가이드는 땀을 내보내고 공기가 통하며 햇빛을 가릴 수 있는 옷을 찾으라고 안내합니다. 탱크톱·쇼츠처럼 짧게 입더라도, 열을 식히는 기능성 원단과 자외선 차단(옷 또는 자외선 차단제)을 함께 언급합니다. 모자, 수분 보충 용품도 이 구간에 등장해요.</p>
<p>한국 대회로는 5~9월 주말 대회가 이 구간에 자주 해당할 수 있어요. 당일 기온은 예보를 보고, <a class="ed-link" href="/marathon-schedule/2026.html">2026 마라톤 일정</a>에서 해당 달을 확인해 주세요.</p></article>
<article id="mild"><h3>약 4.4℃ 초과 15.6℃ 이하</h3><p class="deg">공식 가이드의 봄·가을 구간</p>
<p>공식 가이드는 기온이 낮은 편이면 겹쳐 입되, 통기가 중요하다고 적습니다. 긴팔 또는 반팔 중간층, 가벼운 바지·레깅스, 바람이나 습도가 있으면 가벼운 재킷을 예로 듭니다. 필요하면 벗거나 접을 수 있는 겉옷을 언급해요.</p>
<p>한국 대회로는 4월·10월 전후, 그리고 낮과 아침 기온 차가 큰 달이 해당할 수 있어요. <a class="ed-link" href="/month/2026-10.html">10월 대회 일정</a>과 <a class="ed-link" href="/gear/jacket.html">바람막이 가이드</a>를 함께 볼 수 있어요.</p></article>
<article id="cold"><h3>약 4.4℃ 이하</h3><p class="deg">공식 가이드의 추운 날 구간</p>
<p>공식 가이드는 레이어링을 필수로 봅니다. 베이스(가볍고 땀을 내보내는 층), 미드(열을 가두되 과열을 막을 통기), 기온이 약 0℃ 이하로 떨어질 때는 바람·비·눈을 막는 겉옷을 안내합니다. 손과 귀처럼 말단이 노출되면 체감이 크게 달라진다고도 적어요. 자세한 겨울 안내는 <a class="ed-link" href="/gear/winter.html">겨울 러닝복</a>에 모아 두었습니다.</p>
<p>한국 대회로는 11~3월 일정이 이 구간에 자주 해당할 수 있어요. <a class="ed-link" href="/month/2026-11.html">11월</a>, <a class="ed-link" href="/month/2026-12.html">12월</a>, <a class="ed-link" href="/month/2027-01.html">1월</a> 모아보기를 참고해 주세요. 당일 최저·최고 기온은 대회 페이지의 예보를 우선합니다.</p></article>
</div>
<p>겹쳐 입기의 순서는 공식 가이드를 따릅니다. 안쪽은 땀을 내보내는 층, 가운데는 보온, 바깥은 바람과 비를 막는 층이에요. 얼마나 두껍게 입을지는 공식 숫자가 아니라 본인 컨디션과 그날 예보로 정하는 것이 맞습니다.</p>
<p class="ed-small">관련: <a class="ed-link" href="/gear/">의류 허브</a> · <a class="ed-link" href="/gear/race-day.html">대회 당일 복장</a> · <a class="ed-link" href="/shoes/">러닝화 스펙</a></p>
'''
    title = '기온별 러닝 복장 — 공식 가이드와 한국 대회 달 | Run우리'
    desc = '나이키 코리아 공식 기온 구간(15.6℃ 이상, 4.4~15.6℃, 4.4℃ 이하)을 인용하고, 한국 대회 월별 일정과 연결한 복장 안내. 착화감은 짓지 않습니다.'
    path = '/gear/temperature.html'
    trail = [('Run우리', '/'), ('러닝 복장', '/gear/'), ('기온별 복장', path)]
    return page(title, desc, path, trail, body_wrap(aff, '러닝 복장', '기온별 러닝 복장', lede, inner), [])


def winter(aff):
    lede = (f'11월부터 3월 사이 한국 대회는 아침 기온이 공식 가이드의 추운 날 구간(약 4.4℃ 이하)에 들어가는 날이 많아요. '
            f'레이어링과 말단 보온만 공식 안내 범위에서 정리했습니다. 확인일 {CHECKED_LABEL}.')
    inner = '''
<p>참고: 나이키 코리아 <a class="ed-link" href="https://www.nike.com/kr/a/what-to-wear-by-temperature" rel="noopener noreferrer" target="_blank">기온에 적합한 러닝 복장 추천</a>(마지막 업데이트 2025-07-11). 공식 글의 문장을 복사하지 않고, 항목만 우리 일정과 연결했어요.</p>
<h2>겹쳐 입기</h2>
<ul>
<li>베이스 레이어: 공식 가이드는 가볍고 따뜻하면서 통기가 되는 층을 권합니다. 땀이 피부에 남으면 추워질 수 있어, 면처럼 물을 머금는 소재는 공식 글의 취지와 잘 맞지 않아요.</li>
<li>미드 레이어: 열을 가두되 과열되지 않게 통기가 있어야 한다고 적혀 있습니다. 기온이 약 4.4℃ 이하로 더 떨어지면 중간 층을 더하는 안내가 있습니다.</li>
<li>아우터: 약 0℃ 이하에서는 바람·비·눈을 막는 겉옷을 공식 가이드가 언급합니다. 부피가 커서 동작이 불편해지지 않는 가벼운 겉옷을 고르라는 취지예요. 자세한 겉옷 항목은 <a class="ed-link" href="/gear/jacket.html">바람막이 가이드</a>를 봐 주세요.</li>
</ul>
<h2>손·귀·머리</h2>
<p>공식 가이드는 손과 귀가 노출되면 체감 온도에 큰 영향을 준다고 적습니다. 방수·방풍과 통기를 함께 보는 모자·장갑, 터치스크린을 쓸 수 있는 장갑 끝을 예로 듭니다. 장갑만 따로 정리한 글은 <a class="ed-link" href="/gear/gloves.html">러닝 장갑</a>이에요.</p>
<h2>발</h2>
<p>공식 가이드는 겨울 러닝화에 따뜻함뿐 아니라 미끄러운 지면의 접지력, 겉 소재의 발수 기능을 함께 보라고 안내합니다. 특정 모델의 착화감은 적지 않아요. 로드 모델의 공식 무게·드롭은 <a class="ed-link" href="/shoes/">러닝화 허브</a>에서 확인할 수 있습니다.</p>
<h2>한국 대회 달</h2>
<p>겨울철 일정은 <a class="ed-link" href="/month/2026-11.html">2026년 11월</a>, <a class="ed-link" href="/month/2026-12.html">12월</a>, <a class="ed-link" href="/month/2027-01.html">2027년 1월</a>, <a class="ed-link" href="/month/2027-02.html">2월</a>, <a class="ed-link" href="/month/2027-03.html">3월</a> 모아보기에서 볼 수 있어요. 대회 페이지에 예보가 있으면 그날 최저 기온을 우선하세요. 출발 시각이 이른 대회는 낮 최고 기온만 보고 얇게 입으면 출발선에서 추울 수 있습니다.</p>
<p class="ed-small">관련: <a class="ed-link" href="/gear/temperature.html">기온별 복장</a> · <a class="ed-link" href="/gear/race-day.html">대회 당일 복장</a></p>
'''
    title = '겨울 러닝복 — 레이어링과 한국 겨울 대회 | Run우리'
    desc = '공식 기온 가이드의 추운 날 구간을 인용하고, 11~3월 한국 대회 일정과 연결한 겨울 러닝 복장 안내.'
    path = '/gear/winter.html'
    trail = [('Run우리', '/'), ('러닝 복장', '/gear/'), ('겨울 러닝복', path)]
    return page(title, desc, path, trail, body_wrap(aff, '러닝 복장', '겨울 러닝복', lede, inner), [])


def race_day(aff):
    lede = (f'대회 당일에는 평소 훈련에서 입어 본 조합을 그대로 쓰는 것이 안전해요. 아래는 거리와 예상 기온에 따라 미리 정해 두면 좋은 항목입니다. '
            f'특정 브랜드의 착용감을 지어내지 않았습니다. 확인일 {CHECKED_LABEL}.')
    inner = '''
<p>준비물 전체 점검은 기존의 <a class="ed-link" href="/guide/first-marathon-checklist.html">첫 마라톤 준비 체크리스트</a>를 우선해 주세요. 이 글은 옷과 날씨에 해당하는 부분만 보강합니다.</p>
<h2>출발 전에 정할 것</h2>
<ul>
<li>예상의 기온은 대회 페이지 예보와 공식 발표를 따릅니다. 구간별 옷 조합은 <a class="ed-link" href="/gear/temperature.html">기온별 복장</a>을 기준으로 하세요.</li>
<li>평소 장거리 훈련에서 입었던 상의·하의·양말만 대회에 가져가는 편이 좋아요. 새 옷의 마찰이나 봉제선 문제는 공식 스펙으로 미리 알 수 없습니다.</li>
<li> Bib을 다는 위치, 주머니에 넣을 에너지 보충제, 찬 비에 대비한 얇은 겉옷(출발 전 벗을 수 있는 것)을 미리 정해 두세요.</li>
</ul>
<h2>거리별로 달라지는 점</h2>
<ul>
<li>5km·10km: 몸이 워밍업되는 시간이 짧아요. 출발 기온에 맞춰 입되, 지나친 겉옷은 도중 보관이 어려울 수 있습니다.</li>
<li>하프: 시간이 길어져 햇살이나 바람이 바뀌는 경우가 있어요. <a class="ed-link" href="/shoes/best/half.html">하프 러닝화 스펙</a>과 함께, 중간층 하나를 여분으로 둘지 훈련 때 시험해 보세요.</li>
<li>풀코스: 출발과 후반의 기온·체감이 다를 수 있어요. <a class="ed-link" href="/shoes/best/marathon.html">풀코스 러닝화 스펙</a>, <a class="ed-link" href="/gear/winter.html">겨울 레이어링</a>을 거리와 월별로 같이 보세요. 이 신발을 신으면 기록이 단축된다는 말은 적지 않습니다.</li>
</ul>
<h2>11~3월 대회</h2>
<p>아침 최저기온이 공식 가이드의 4.4℃ 이하 구간에 들어가면 장갑·비니·타이츠를 공식 안내 항목으로 검토해 주세요. 월별 일정은 <a class="ed-link" href="/month/2026-11.html">11월</a>부터 <a class="ed-link" href="/month/2027-03.html">3월</a> 허브에 있습니다.</p>
<p class="ed-small">관련: <a class="ed-link" href="/gear/gloves.html">장갑</a> · <a class="ed-link" href="/gear/jacket.html">바람막이</a> · <a class="ed-link" href="/distance/half.html">하프 대회</a> · <a class="ed-link" href="/distance/full.html">풀코스 대회</a></p>
'''
    title = '대회 당일 복장·준비물 — 거리와 기온 | Run우리'
    desc = '5km부터 풀코스까지, 공식 기온 가이드를 기준으로 대회 당일 복장과 준비물을 정리한 안내. 새 옷의 착화감은 짓지 않습니다.'
    path = '/gear/race-day.html'
    trail = [('Run우리', '/'), ('러닝 복장', '/gear/'), ('대회 당일 복장', path)]
    return page(title, desc, path, trail, body_wrap(aff, '러닝 복장', '대회 당일 복장·준비물', lede, inner), [])


def gloves(aff):
    lede = (f'추운 날 장갑은 체감에 큰 영향을 줍니다. 공식 가이드가 말하는 항목(방풍·방수·통기, 터치스크린)만 고르는 기준으로 적었어요. '
            f'특정 제품의 따뜻함은 짓지 않았습니다. 확인일 {CHECKED_LABEL}.')
    inner = '''
<p>나이키 코리아 공식 기온 가이드는 손끝이 노출되면 체감이 달라진다고 적습니다. 혈액이 몸 중심으로 모이면 손가락이 더 빨리 시려질 수 있다는 설명이에요. 출처: <a class="ed-link" href="https://www.nike.com/kr/a/what-to-wear-by-temperature" rel="noopener noreferrer" target="_blank">기온에 적합한 러닝 복장 추천</a>.</p>
<h2>고를 때 보는 항목</h2>
<ul>
<li>바람과 습기를 막는지(공식 가이드는 방수·방풍과 가벼운 통기를 함께 언급합니다).</li>
<li>터치스크린을 장갑을 벗지 않고 쓸 수 있는지. 공식 가이드도 장갑 끝의 터치 기능을 예로 듭니다.</li>
<li>반사 소재가 있는지. 이른 아침·저녁 훈련, 겨울 대회 출발 전에 유용할 수 있어요.</li>
<li>손목이 소매 안으로 들어가는지, 벗어 주머니에 넣을 수 있는 크기인지. 이는 사용 편의이며, 따뜻함의 수치는 아닙니다.</li>
</ul>
<p>얇은 라이너와 겉장갑을 겹쳐 쓰는 방식은 공식 가이드가 레이어링을 말한 취지와 맞아요. 다만 ‘몇 도까지 버틴다’는 식의 숫자는 공식 페이지에 없으면 적지 않습니다.</p>
<p>겨울 대회 일정은 <a class="ed-link" href="/gear/winter.html">겨울 러닝복</a>, 기온 구간은 <a class="ed-link" href="/gear/temperature.html">기온별 복장</a>을 함께 봐 주세요.</p>
'''
    title = '러닝 장갑 고르는 기준 — 방풍·터치·겨울 대회 | Run우리'
    desc = '공식 기온 가이드를 근거로 러닝 장갑을 고를 때 보는 항목만 정리했습니다. 특정 제품의 착화감은 적지 않습니다.'
    path = '/gear/gloves.html'
    trail = [('Run우리', '/'), ('러닝 복장', '/gear/'), ('러닝 장갑', path)]
    return page(title, desc, path, trail, body_wrap(aff, '러닝 복장', '러닝 장갑 고르는 기준', lede, inner), [])


def jacket(aff):
    lede = (f'바람과 가벼운 비에 대비하는 겉옷은, 공식 가이드가 봄·가을과 영하권에서 다르게 설명합니다. '
            f'소재의 감촉은 짓지 않고, 고를 때 보는 공식 항목만 적었어요. 확인일 {CHECKED_LABEL}.')
    inner = '''
<p>출처: 나이키 코리아 <a class="ed-link" href="https://www.nike.com/kr/a/what-to-wear-by-temperature" rel="noopener noreferrer" target="_blank">기온에 적합한 러닝 복장 추천</a>. 공식 글은 4.4~15.6℃ 구간에서 바람과 습도가 있으면 가벼운 재킷을 예로 들고, 약 0℃ 이하에서는 바람·비·눈을 막는 겉옷을 안내합니다. 제품명 예시는 공식 글의 맥락을 밝히는 용도이며, 우리가 착화감을 평가한 것이 아니에요.</p>
<h2>고를 때 보는 항목</h2>
<ul>
<li>바람을 막는지, 가벼운 비를 막는다고 공식 상품 페이지가 적는지. 방수 등급 숫자는 해당 상품의 공식 표기가 있을 때만 인용하세요.</li>
<li>땀을 밖으로 내보낼 수 있는지(통기). 겉옷이 너무 막히면 안에서 식은 땀이 남습니다.</li>
<li>입고 달리다가 벗었을 때 손에 쥐거나 허리에 묶기 쉬운 무게와 부피. 정확한 그램은 공식 표기가 있는 상품만 적습니다.</li>
<li>어두운 시간대를 위한 반사 세부. 공식 가이드도 360도 반사를 예로 듭니다.</li>
</ul>
<p>여름철(공식 구간 15.6℃ 이상)에는 겉옷보다 자외선과 수분 보충이 우선이라는 것이 같은 가이드의 취지예요. 겨울 레이어링의 바깥층으로는 <a class="ed-link" href="/gear/winter.html">겨울 러닝복</a>을, 기온이 애매한 달은 <a class="ed-link" href="/gear/temperature.html">기온별 복장</a>을 봐 주세요.</p>
<p class="ed-small">의류 개별 상품 페이지는 이번 단계에서 만들지 않았어요. 쿠팡 파트너스 가입 뒤에 카테고리 링크를 넣을 자리를 페이지 상단에 마련해 두었고, 지금은 숨겨 두었습니다.</p>
'''
    title = '러닝 바람막이 — 바람·비에 대비할 때 보는 항목 | Run우리'
    desc = '공식 기온 가이드를 근거로 러닝 바람막이를 고를 때 보는 항목만 정리했습니다. 소재 감촉은 짓지 않습니다.'
    path = '/gear/jacket.html'
    trail = [('Run우리', '/'), ('러닝 복장', '/gear/'), ('러닝 바람막이', path)]
    return page(title, desc, path, trail, body_wrap(aff, '러닝 복장', '러닝 바람막이', lede, inner), [])


def hub(aff):
    cards = ''.join(
        f'<a class="sg-card" href="/gear/{slug}.html"><div class="br">가이드</div><h3>{esc(title)}</h3>'
        f'<p class="ed-small">{esc(desc)}</p></a>'
        for slug, title, desc in GUIDES
    )
    lede = (f'상황별 복장 가이드 5편이에요. 개별 의류 상품 페이지는 아직 만들지 않았고, 공식 자료에 있는 구간·항목만 적었습니다. '
            f'확인일 {CHECKED_LABEL}.')
    body = (f'{disclosure(aff)}<header class="ed-page-head" style="padding:18px var(--page-x) 0">'
            f'<div class="ed-label">러닝 복장</div><h1 class="ed-h1" style="margin:12px 0 10px">러닝 복장·장비 가이드</h1>'
            f'<p class="ed-lede">{lede}</p>'
            f'<p class="ed-small">기존 글과도 연결해 두었어요. '
            f'<a class="ed-link" href="/guide/summer-winter-running.html">여름·겨울 러닝</a>, '
            f'<a class="ed-link" href="/guide/first-marathon-checklist.html">첫 대회 준비</a>, '
            f'<a class="ed-link" href="/shoes/">러닝화 공식 스펙</a>.</p></header>'
            f'<div class="sg-grid" style="padding:8px var(--page-x) 24px">{cards}</div>')
    title = '러닝 복장 가이드 — 기온별·겨울·대회 당일 | Run우리'
    desc = '기온별 복장, 겨울 러닝복, 대회 당일 준비물, 장갑, 바람막이. 공식 가이드를 인용하고 착화감은 짓지 않습니다.'
    path = '/gear/'
    trail = [('Run우리', '/'), ('러닝 복장', '/gear/')]
    return page(title, desc, path, trail, body, [])


def main():
    _, aff = load_shoes()
    paths = [
        hub(aff),
        temperature(aff),
        winter(aff),
        race_day(aff),
        gloves(aff),
        jacket(aff),
    ]
    man_path = ROOT / 'data/p3_urls.json'
    man = json.loads(man_path.read_text(encoding='utf8')) if man_path.exists() else {'paths': []}
    man['paths'] = list(dict.fromkeys(man.get('paths', []) + paths))
    man['gear_pages'] = paths
    man_path.write_text(json.dumps(man, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('build_gear:', len(paths), 'pages')


if __name__ == '__main__':
    main()
