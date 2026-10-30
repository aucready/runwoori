#!/usr/bin/env bash
# 사용법: tools/set_adsense.sh PUBID      예) tools/set_adsense.sh pub-1234567890123456
#         tools/set_adsense.sh --off      광고 스크립트를 다시 주석(비활성)으로 되돌림
# 하는 일: 모든 페이지 <head> 의 AdSense 스니펫 주석을 활성화하고 ads.txt 를 채웁니다.
#   PUBID 는 pub-숫자16자리 / ca-pub-숫자16자리 / 숫자16자리 모두 가능.
# 주의: AdSense 사이트 승인(또는 사이트 추가·코드 확인 단계)에 맞춰 실행하세요.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARG="${1:-}"
if [ -z "$ARG" ] || [ "$ARG" = "-h" ] || [ "$ARG" = "--help" ]; then sed -n '2,7p' "$0"; exit 1; fi
if [ "$ARG" = "--off" ]; then MODE=off; PUB=""; else
  MODE=on; PUB="$(printf '%s' "$ARG" | tr 'A-Z' 'a-z' | sed -E 's/^ca-//; s/^pub-//')"
  if ! printf '%s' "$PUB" | grep -Eq '^[0-9]{16}$'; then echo "게시자 ID 는 숫자 16자리여야 해요. 예: pub-1234567890123456 (입력: $ARG)" >&2; exit 1; fi
fi
python3 - "$ROOT" "$MODE" "$PUB" <<'PY'
import sys, os, re, glob
root, mode, pub = sys.argv[1:4]
SRC = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-'
n = 0
for f in sorted(glob.glob(os.path.join(root, '*.html'))):
    s = open(f, encoding='utf-8').read()
    if 'ADSENSE:START' not in s: continue
    if mode == 'on':
        body = f'<script async src="{SRC}{pub}" crossorigin="anonymous"></script>'
    else:
        body = f'<!-- <script async src="{SRC}XXXX" crossorigin="anonymous"></script> -->'
    t = re.sub(r'<!--ADSENSE:START-->.*?<!--ADSENSE:END-->', lambda m: '<!--ADSENSE:START-->' + body + '<!--ADSENSE:END-->', s, flags=re.S)
    if t != s: open(f, 'w', encoding='utf-8').write(t); n += 1
ads = os.path.join(root, 'ads.txt')
line = 'google.com, pub-%s, DIRECT, f08c47fec0942fa0' % (pub if mode == 'on' else 'XXXXXXXXXXXXXXXX')
open(ads, 'w').write(line + '\n')
print(('활성화' if mode == 'on' else '비활성화') + f': 페이지 {n}개 수정, ads.txt = {line}')
PY
if [ "$MODE" = on ]; then cat <<EOF

────────── 다음 단계 ──────────
1) 올리기:  git add -A && git commit -m "AdSense 코드 활성화" && git push
2) 1~2분 뒤 확인:  https://도메인/ads.txt 가 열리고, 페이지 소스(<head>)에 adsbygoogle.js 가 보이는지
3) AdSense 화면에서 "코드를 붙여넣었습니다" → 확인 → 검토 요청
4) 검토 중에는 광고 단위(ins 태그)를 직접 넣지 않아도 돼요. 승인 후 자동 광고를 켜거나 광고 단위를 추가하세요.
EOF
else echo "광고 스크립트를 주석으로 되돌렸어요. 커밋·푸시하면 반영돼요."; fi
