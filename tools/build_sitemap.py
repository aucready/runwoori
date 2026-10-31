#!/usr/bin/env python3
"""sitemap.xml 생성 — 주소 앞부분은 자리표시자 {{SITE_URL}} (tools/set_domain.sh 가 실제 도메인으로 바꿈).
러닝 가이드 글을 추가하거나 페이지를 늘린 뒤에 다시 실행: python3 tools/build_sitemap.py
(대회 상세는 race/<id>.html 정적 페이지로 포함, saved.html 은 개인 저장 목록이라 제외)"""
import json, os, datetime
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
BASE=os.environ.get('SITE_URL','https://runwoori.com').rstrip('/')
today=datetime.date.today().isoformat()
pages=[('', 'daily','1.0'),('overseas.html','daily','0.8'),('my.html','weekly','0.7'),('blog.html','weekly','0.9'),('courses.html','monthly','0.6'),
       ('tools.html','monthly','0.6'),('guide.html','monthly','0.5'),('about.html','monthly','0.4'),('contact.html','yearly','0.3'),
       ('privacy.html','yearly','0.3'),('terms.html','yearly','0.3')]
urls=[(BASE+'/'+p,'', cf, pr) for p,cf,pr in pages]
idx=json.load(open(os.path.join(ROOT,'data','blog','index.json'),encoding='utf-8'))
for p in idx['posts']:
    urls.append((f"{BASE}/post.html?id={p['id']}", p.get('date',today), 'monthly','0.7'))
# 대회별 정적 페이지 (tools/build_race_pages.py 가 만든 data/race_pages.json, 색인 허용된 것만)
rp=os.path.join(ROOT,'data','race_pages.json')
if os.path.exists(rp):
    for pg in json.load(open(rp,encoding='utf-8'))['pages']:
        if pg.get('indexable'):
            urls.append((BASE+'/race/'+pg['id']+'.html', pg.get('lastmod') or today, 'daily' if not pg.get('ended') else 'yearly', '0.6' if not pg.get('ended') else '0.3'))
op=os.path.join(ROOT,'data','overseas_pages.json')
if os.path.exists(op):
    for pg in json.load(open(op,encoding='utf-8'))['pages']:
        urls.append((BASE+'/overseas/'+pg['slug']+'.html', pg.get('lastmod') or today, 'weekly' if not pg.get('ended') else 'yearly', '0.6' if not pg.get('ended') else '0.3'))
# 랜딩 페이지(마감 임박·월별·지역별, tools/build_landing.py 가 만든 data/landing_pages.json, 색인 허용된 것만)
lp=os.path.join(ROOT,'data','landing_pages.json')
if os.path.exists(lp):
    for pg in json.load(open(lp,encoding='utf-8'))['pages']:
        if pg.get('indexable'):
            urls.append((pg['url'], pg.get('lastmod') or today, pg.get('changefreq','daily'), pg.get('priority','0.7')))
out=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc,lm,cf,pr in urls:
    out.append('  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>'%(loc,lm or today,cf,pr))
out.append('</urlset>')
open(os.path.join(ROOT,'sitemap.xml'),'w',encoding='utf-8').write('\n'.join(out)+'\n')
print('sitemap.xml:',len(urls),'urls')
