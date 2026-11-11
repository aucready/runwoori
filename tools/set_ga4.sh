#!/usr/bin/env bash
# 사용법: tools/set_ga4.sh G-XXXXXXXXXX   (켜기/갱신)     tools/set_ga4.sh --off   (끄기)
# 하는 일: 루트 *.html 의 <head> 에 <!--GA4:START-->…<!--GA4:END--> 블록을 넣거나 갱신/제거합니다.
#   위치: <!--ADSENSE:END--> 바로 뒤, 없으면 </head> 바로 앞. (리다이렉트 전용 페이지는 건너뜀)
#   생성 페이지(race/ overseas/ month/ region/)는 생성기가 index.html 의 GA4 블록을 읽어 자동으로 넣습니다.
#   AdSense 조각은 index.html 이 아니라 about.html 에서 읽습니다(홈 등 얇은 화면은 광고 없음).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARG="${1:-}"
if [ -z "$ARG" ] || [ "$ARG" = "-h" ]; then sed -n '2,6p' "$0"; exit 1; fi
if [ "$ARG" != "--off" ] && ! printf '%s' "$ARG" | grep -Eq '^G-[A-Z0-9]{6,}$'; then echo "측정 ID 형식은 G-XXXXXXXXXX 예요 (입력: $ARG)" >&2; exit 1; fi
python3 - "$ROOT" "$ARG" <<'PY'
import sys, os, re, glob
root, arg = sys.argv[1:3]
off = arg == '--off'
BLOCK = ('<!--GA4:START--><script async src="https://www.googletagmanager.com/gtag/js?id=%(i)s"></script>\n'
         '<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag(\'js\',new Date());gtag(\'config\',\'%(i)s\',{anonymize_ip:true});</script><!--GA4:END-->')
n = 0
for f in sorted(glob.glob(os.path.join(root, '*.html'))):
    s = open(f, encoding='utf-8').read()
    if 'http-equiv="refresh"' in s or '</head>' not in s: continue
    s0 = re.sub(r'\n?<!--GA4:START-->.*?<!--GA4:END-->', '', s, flags=re.S)
    if off: t = s0
    else:
        b = BLOCK % {'i': arg}
        if '<!--ADSENSE:END-->' in s0: t = s0.replace('<!--ADSENSE:END-->', '<!--ADSENSE:END-->\n' + b, 1)
        else: t = s0.replace('</head>', b + '\n</head>', 1)
    if t != s: open(f, 'w', encoding='utf-8').write(t); n += 1
print(('끔' if off else '켬 ' + arg) + f': 페이지 {n}개 수정')
PY
