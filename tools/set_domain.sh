#!/usr/bin/env bash
# 사용법: tools/set_domain.sh 도메인 [문의용이메일]
#   예)  tools/set_domain.sh runwoori.com contact@runwoori.com
# 하는 일
#   1) sitemap.xml / robots.txt 의 {{SITE_URL}} 을 https://도메인 으로 교체
#   2) 모든 페이지의 <link rel="canonical">·og:url 을 넣고 og:image / twitter:image 를 절대 주소로 교체
#   3) 이메일을 주면 {{CONTACT_EMAIL}} 을 채우고 "자리표시자" 안내 문구를 지움
#   4) CNAME 파일 작성 (GitHub Pages 사용자 지정 도메인)
# 다시 실행해도 안전함(도메인을 바꿀 때도 사용 가능). 도메인은 www 없는 주소(apex)를 기준으로 함.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="${1:-}"; EMAIL="${2:-${CONTACT_EMAIL:-}}"
if [ -z "$RAW" ] || [ "$RAW" = "-h" ] || [ "$RAW" = "--help" ]; then sed -n '2,12p' "$0"; exit 1; fi
DOMAIN="$(printf '%s' "$RAW" | tr 'A-Z' 'a-z' | sed -E 's#^https?://##; s#/.*$##; s#^www\.##')"
if ! printf '%s' "$DOMAIN" | grep -Eq '^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$'; then
  echo "도메인 형식이 올바르지 않아요: $RAW  (예: runwoori.com — 한글 도메인은 영문 변환(punycode) 주소를 넣어 주세요)" >&2; exit 1; fi
if [ -n "$EMAIL" ] && ! printf '%s' "$EMAIL" | grep -Eq '^[^@ ]+@[^@ ]+\.[^@ ]+$'; then echo "이메일 형식이 올바르지 않아요: $EMAIL" >&2; exit 1; fi
if [ "$RAW" != "$DOMAIN" ]; then echo "※ 입력값 '$RAW' → '$DOMAIN' 으로 정리했어요(https:// 와 www. 는 빼요)."; fi

python3 - "$ROOT" "$DOMAIN" "$EMAIL" <<'PY'
import sys, os, re, glob
root, domain, email = sys.argv[1:4]
base = 'https://' + domain
old = None
if os.path.exists(os.path.join(root, 'CNAME')):
    o = open(os.path.join(root, 'CNAME')).read().strip()
    if o and o != domain: old = 'https://' + o
n_html = 0
for f in sorted(glob.glob(os.path.join(root, '*.html'))):
    name = os.path.basename(f)
    s = open(f, encoding='utf-8').read(); orig = s
    if 'CANONICAL:START' in s:
        path = '' if name == 'index.html' else name
        tag = f'<link rel="canonical" href="{base}/{path}"><meta property="og:url" content="{base}/{path}">'
        s = re.sub(r'<!--CANONICAL:START-->.*?<!--CANONICAL:END-->', lambda m: '<!--CANONICAL:START-->' + tag + '<!--CANONICAL:END-->', s, flags=re.S)
    s = re.sub(r'(<meta (?:property="og:image"|name="twitter:image") content=")(?:https?://[^"/]+/)?assets/icons/og-image\.png"',
               lambda m: m.group(1) + base + '/assets/icons/og-image.png"', s)
    if old: s = s.replace(old, base)
    if email:
        s = re.sub(r'<!--PLACEHOLDER-NOTICE:START-->.*?<!--PLACEHOLDER-NOTICE:END-->', '', s, flags=re.S)
        s = s.replace('{{CONTACT_EMAIL}}', email)
    if s != orig:
        open(f, 'w', encoding='utf-8').write(s); n_html += 1
for name in ('sitemap.xml', 'robots.txt'):
    p = os.path.join(root, name)
    if os.path.exists(p):
        s = open(p, encoding='utf-8').read().replace('{{SITE_URL}}', base)
        if old: s = s.replace(old, base)
        open(p, 'w', encoding='utf-8').write(s)
open(os.path.join(root, 'CNAME'), 'w').write(domain + '\n')
left = []
for f in glob.glob(os.path.join(root, '*')):
    if os.path.isfile(f) and os.path.splitext(f)[1] in ('.html', '.xml', '.txt'):
        t = open(f, encoding='utf-8', errors='ignore').read()
        for ph in ('{{SITE_URL}}', '{{CONTACT_EMAIL}}'):
            if ph in t: left.append(f'{os.path.basename(f)}: {ph}')
print(f'완료: 페이지 {n_html}개 수정, sitemap.xml·robots.txt 갱신, CNAME={domain}')
if left: print('아직 남은 자리표시자 →', ', '.join(left))
PY

cat <<EOF

────────── 다음 단계 ──────────
1) 변경 내용 올리기:  git add -A && git commit -m "도메인 연결: $DOMAIN" && git push
2) 도메인 DNS(구입한 곳)에 A 레코드 4개(185.199.108.153 / .109 / .110 / .111)와
   CNAME www → aucready.github.io 를 등록하세요.
3) GitHub 저장소 Settings → Pages → Custom domain 에 $DOMAIN 입력 → Save,
   DNS 확인이 끝나면 "Enforce HTTPS" 체크.
4) 열어서 확인:  https://$DOMAIN/  ·  https://$DOMAIN/sitemap.xml  ·  https://$DOMAIN/robots.txt
5) Google Search Console 에 https://$DOMAIN 등록 → sitemap.xml 제출.
6) AdSense 가입 후:  tools/set_adsense.sh pub-XXXXXXXXXXXXXXXX  → 커밋·푸시
$( [ -z "$EMAIL" ] && echo "※ 이메일을 아직 안 넣었어요. 문의·개인정보 페이지에 {{CONTACT_EMAIL}} 이 남아 있어요 →  tools/set_domain.sh $DOMAIN 이메일@주소" )
자세한 순서: ADSENSE_GUIDE.md
EOF
