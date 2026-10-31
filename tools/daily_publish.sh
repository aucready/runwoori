#!/usr/bin/env bash
# 매일 한 번: (선택) 수집 → 대회별 정적 페이지 + sitemap 생성 → 배포 저장소로 복사 → git commit & push (runwoori.com)
#
#   /workspace/running-site/tools/daily_publish.sh            # 수집은 이미 끝났다고 보고, 지금 data/races.json 으로 빌드·배포
#   /workspace/running-site/tools/daily_publish.sh --collect  # 수집기(run_collect.sh)부터 돌린 뒤 빌드·배포
#
# 경로를 바꾸려면 환경변수 SRC(원본 사이트 폴더), DEPLOY(GitHub Pages 배포 저장소), SITE_URL 사용.
set -euo pipefail
SRC="${SRC:-/workspace/running-site}"
DEPLOY="${DEPLOY:-/workspace/runwoori-deploy}"
export SITE_URL="${SITE_URL:-https://runwoori.com}"
DOMAIN="${SITE_URL#https://}"

if [ "${1:-}" = "--collect" ]; then
  echo "== 1) 대회 데이터 수집"; /workspace/running-site-collector/run_collect.sh
fi

cd "$SRC"
echo "== 1a) 새 장소 좌표(캐시에 없는 곳만) + 날씨 예보 수집 — 실패해도 계속 진행"
timeout 300 python3 tools/geocode_venues.py --max 40 || echo "  (장소 지오코딩 건너뜀)"
timeout 600 python3 tools/fetch_weather.py || echo "  (날씨 수집 건너뜀 — 날씨 없이 빌드해요)"
echo "== 2) 대회별 정적 페이지 생성"; python3 tools/build_race_pages.py
echo "== 2a) 해외 주요 대회 페이지 생성"; python3 tools/build_overseas.py
echo "== 2a-2) 랜딩 페이지(마감 임박·월별·지역별) 생성"; python3 tools/build_landing.py
echo "== 2b) 공식 홈페이지 링크 점검"
python3 - <<'PY'
import json, sys
d = json.load(open('data/races.json', encoding='utf8'))['races']
n = sum(1 for r in d if (r.get('official_url') or '').startswith('http'))
print(f'공식 홈페이지 링크 {n}/{len(d)}')
if d and n / len(d) < 0.85:
    print('공식 홈페이지 링크 비율이 85% 미만이에요. 수집기를 확인하세요. 중단합니다.', file=sys.stderr); sys.exit(1)
PY
echo "== 3) sitemap.xml 생성";        python3 tools/build_sitemap.py
sed -i "s#{{SITE_URL}}#${SITE_URL}#g" sitemap.xml        # 자리표시자가 남아 있으면 실제 주소로
if grep -q '{{' sitemap.xml; then echo "sitemap.xml 에 자리표시자가 남아 있어요. 중단합니다." >&2; exit 1; fi
N_RACE=$(ls race/*.html | wc -l)
if [ "$N_RACE" -lt 20 ]; then echo "대회 페이지가 너무 적어요($N_RACE). 수집 실패로 보고 배포를 중단합니다." >&2; exit 1; fi

echo "== 4) 배포 저장소로 복사 ($DEPLOY)"
mkdir -p "$DEPLOY/data"
rm -rf "$DEPLOY/race" && cp -a race "$DEPLOY/race"
rm -rf "$DEPLOY/overseas" && cp -a overseas "$DEPLOY/overseas" && cp overseas.html "$DEPLOY/overseas.html"
[ -f data/weather.json ] && cp data/weather.json "$DEPLOY/data/"   # 날씨 예보(목록 카드용)
cp data/races.json data/race_archive.json data/race_pages.json data/overseas.json data/overseas_pages.json "$DEPLOY/data/"
[ -f data/prior_year.json ] && cp data/prior_year.json "$DEPLOY/data/"
cp *.html data.js app.js site.css "$DEPLOY/"; cp tools/set_ga4.sh "$DEPLOY/tools/" 2>/dev/null || true; cp data/courses.json "$DEPLOY/data/"   # 화면 코드도 함께(수정 누락 방지)
[ -d data/blog ] && { rm -rf "$DEPLOY/data/blog" && cp -a data/blog "$DEPLOY/data/blog"; }
rm -rf "$DEPLOY/month" "$DEPLOY/region" && cp -a month "$DEPLOY/month" && cp -a region "$DEPLOY/region" && cp deadline.html "$DEPLOY/deadline.html" && cp data/landing_pages.json "$DEPLOY/data/"
cp sitemap.xml "$DEPLOY/sitemap.xml"
cp tools/build_race_pages.py tools/build_overseas.py tools/build_landing.py tools/build_sitemap.py tools/daily_publish.sh tools/weather_lib.py tools/fetch_weather.py tools/geocode_venues.py "$DEPLOY/tools/" 2>/dev/null || true

cd "$DEPLOY"
echo "$DOMAIN" > CNAME                                    # 커스텀 도메인 파일 유지
echo "== 5) git commit & push"
git add -A
if git diff --cached --quiet; then
  echo "변경 없음 — 푸시할 것이 없어요."
else
  git commit -q -m "daily: races + race pages $(TZ=Asia/Seoul date +%F) (${N_RACE} pages)"
  git pull -q --rebase origin main
  git push -q origin main
  echo "푸시 완료: $(git log --oneline -1)"
fi
