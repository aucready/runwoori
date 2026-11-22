#!/usr/bin/env python3
"""sitemap.xml 생성 — 주소 앞부분은 자리표시자 {{SITE_URL}} (tools/set_domain.sh 가 실제 도메인으로 바꿈).
러닝 가이드 글을 추가하거나 페이지를 늘린 뒤에 다시 실행: python3 tools/build_sitemap.py
(대회 상세는 race/<id>.html 정적 페이지로 포함, saved.html 은 개인 저장 목록이라 제외)

lastmod (SEO P0, 2026-11-22): 매일 오늘 날짜로 바꾸지 않는다. 주소마다 '내용 해시'를 data/sitemap_state.json 에 적어 두고
해시가 바뀐 날만 lastmod 를 오늘로 올린다.
- 대회: data/race_pages.json 의 hash(대회 정보·접수 상태), 월별·지역·마감: data/landing_pages.json 의 hash(목록 대회·상태)
- 메인: data/races.json 대회 목록(이름·날짜·접수 상태), 그 밖의 정적 화면: 파일 내용(정적 메뉴 블록·?v= 제외)
- 가이드는 글의 dateModified, 해외 대회는 공식 확인일(verified) 그대로."""
import json, os, re, hashlib, datetime
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
BASE=os.environ.get('SITE_URL','https://runwoori.com').rstrip('/')
today=datetime.date.today().isoformat()
STATE_P=os.path.join(ROOT,'data','sitemap_state.json')
state=json.load(open(STATE_P,encoding='utf-8')) if os.path.exists(STATE_P) else {}
new_state={}

def sha(s): return hashlib.sha1(s.encode('utf-8')).hexdigest()[:16]

def lm_for(loc, h):
    old=state.get(loc)
    lm=old['lastmod'] if old and old.get('hash')==h else today
    new_state[loc]={'hash':h,'lastmod':lm}
    return lm

def file_hash(rel):
    p=os.path.join(ROOT,rel if rel and not rel.endswith('/') else rel+'index.html')
    try: s=open(p,encoding='utf-8').read()
    except OSError: return 'missing'
    s=re.sub(r'<!--RWNAV:(HEAD|FOOT)-->.*?<!--/RWNAV:\1-->','',s,flags=re.S)
    s=re.sub(r'\?v=\w+','',s)
    return sha(s)

def home_hash():
    rs=json.load(open(os.path.join(ROOT,'data','races.json'),encoding='utf-8'))['races']
    key='|'.join(f"{r['id']}:{r.get('name')}:{r.get('date')}:{r.get('reg_state')}:{r.get('reg_open')}:{r.get('reg_close')}" for r in sorted(rs,key=lambda r:r['id']))
    return sha(key)

pages=[('', 'daily','1.0'),('overseas.html','daily','0.8'),('my.html','weekly','0.7'),('blog.html','weekly','0.9'),('courses.html','monthly','0.6'),
       ('tools.html','monthly','0.6'),('crew/','monthly','0.5'),('guide.html','monthly','0.5'),('about.html','monthly','0.4'),('install.html','monthly','0.3'),('contact.html','yearly','0.3'),
       ('privacy.html','yearly','0.3'),('terms.html','yearly','0.3')]
urls=[]
for p,cf,pr in pages:
    loc=BASE+'/'+p
    urls.append((loc, lm_for(loc, home_hash() if p=='' else file_hash(p)), cf, pr))
idx=json.load(open(os.path.join(ROOT,'data','blog','index.json'),encoding='utf-8'))
for p in idx['posts']:   # 러닝 가이드: tools/build_guides.py 가 만든 정적 글 페이지 guide/<id>.html
    lm = p.get('dateModified') or p.get('date_modified') or p.get('date') or today
    urls.append((f"{BASE}/guide/{p['id']}.html", lm, 'monthly','0.7'))
# 대회별 정적 페이지 (tools/build_race_pages.py 가 만든 data/race_pages.json, 색인 허용된 것만)
rp=os.path.join(ROOT,'data','race_pages.json')
if os.path.exists(rp):
    for pg in json.load(open(rp,encoding='utf-8'))['pages']:
        if pg.get('indexable'):
            loc=BASE+'/race/'+pg['id']+'.html'
            lm=lm_for(loc, pg['hash']) if pg.get('hash') else (pg.get('lastmod') or today)
            urls.append((loc, lm, 'daily' if not pg.get('ended') else 'yearly', '0.6' if not pg.get('ended') else '0.3'))
op=os.path.join(ROOT,'data','overseas_pages.json')
if os.path.exists(op):
    for pg in json.load(open(op,encoding='utf-8'))['pages']:
        urls.append((BASE+'/overseas/'+pg['slug']+'.html', pg.get('lastmod') or today, 'weekly' if not pg.get('ended') else 'yearly', '0.6' if not pg.get('ended') else '0.3'))
# 랜딩 페이지(마감 임박·월별·지역별, tools/build_landing.py 가 만든 data/landing_pages.json, 색인 허용된 것만)
lp=os.path.join(ROOT,'data','landing_pages.json')
if os.path.exists(lp):
    for pg in json.load(open(lp,encoding='utf-8'))['pages']:
        if pg.get('indexable'):
            lm=lm_for(pg['url'], pg['hash']) if pg.get('hash') else (pg.get('lastmod') or today)
            urls.append((pg['url'], lm, pg.get('changefreq','daily'), pg.get('priority','0.7')))
out=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for loc,lm,cf,pr in urls:
    out.append('  <url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>'%(loc,lm or today,cf,pr))
out.append('</urlset>')
open(os.path.join(ROOT,'sitemap.xml'),'w',encoding='utf-8').write('\n'.join(out)+'\n')
json.dump(new_state,open(STATE_P,'w',encoding='utf-8'),ensure_ascii=False,indent=0,sort_keys=True)
changed=sum(1 for k,v in new_state.items() if v['lastmod']==today)
print('sitemap.xml:',len(urls),'urls · lastmod 오늘로 갱신',changed,'개(내용 해시 변경·신규)')
