#!/usr/bin/env python3
"""고아 대회 페이지 점검 (SEO P0, 2026-11-22).

  python3 tools/check_links.py        # 종료 코드 0 = 고아 0개

색인 허용(race_pages.json indexable) race/<id>.html 이 정적 목록 페이지(index.html·month/·region/·deadline.html)
가운데 적어도 하나에서 <a href> 로 링크되는지 본다. 다른 대회 페이지의 '관련 대회' 링크는 세지 않는다."""
import glob, json, os, re, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
hubs = [os.path.join(ROOT, 'index.html'), os.path.join(ROOT, 'deadline.html')] + glob.glob(os.path.join(ROOT, 'month', '*.html')) + glob.glob(os.path.join(ROOT, 'region', '*.html'))
linked = set()
for h in hubs:
    linked |= set(re.findall(r'href="/?race/([A-Za-z0-9_-]+)\.html"', open(h, encoding='utf8').read()))
pages = json.load(open(os.path.join(ROOT, 'data', 'race_pages.json'), encoding='utf8'))['pages']
idx = [p['id'] for p in pages if p.get('indexable')]
orph = [i for i in idx if i not in linked]
noidx = [p['id'] for p in pages if not p.get('indexable')]
print(f'목록 페이지 {len(hubs)}개 · 색인 대회 페이지 {len(idx)}개 중 목록에서 링크된 것 {len(idx) - len(orph)}개 · 고아 {len(orph)}개 (noindex 페이지 {len(noidx)}개는 제외)')
for i in orph: print('  고아:', i)
sys.exit(1 if orph else 0)
