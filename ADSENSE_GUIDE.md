# Run우리 · 도메인 연결부터 AdSense 승인까지 (사용자 할 일 순서)

사이트 쪽 준비(필수 페이지, sitemap/robots, ads.txt 틀, AdSense 코드 자리, 가이드 글 28편)는 끝나 있어요.
아래는 **도메인을 산 뒤** 직접 해야 하는 순서예요. 명령은 저장소 폴더(`/workspace/runwoori-deploy`)에서 실행해요.

## 0. 미리 정해 둘 것
- **도메인**: 예) `runwoori.com`, `runwoori.kr` (www 없는 주소를 기준으로 써요).
- **문의용 이메일**: 문의하기·개인정보처리방침 페이지에 실제로 공개돼요. 도메인 메일이 없다면 새 Gmail 하나를 만들어도 돼요. 이메일 주소가 비어 있으면 AdSense 심사에서 “연락처가 없다”로 불리해질 수 있어요.

## 1. 도메인 구입 후 DNS 설정 (도메인을 산 곳의 DNS 관리 화면)
| 종류 | 호스트 | 값 |
|---|---|---|
| A | @ (루트) | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | aucready.github.io |

- 기존에 같은 호스트(@, www)로 걸려 있던 레코드(주차 페이지 등)는 지워요.
- 반영까지 몇 분~최대 24시간 걸려요. 확인: `dig runwoori.com +short` 에 위 IP 4개가 나오면 돼요.
- (선택) IPv6용 AAAA 레코드도 GitHub 안내에 있어요. 없어도 동작해요.

## 2. 사이트 파일에 도메인 채우기 (`set_domain.sh`)
```bash
cd /workspace/runwoori-deploy
tools/set_domain.sh runwoori.com contact@runwoori.com   # 도메인, 문의 이메일
git add -A && git commit -m "도메인 연결: runwoori.com" && git push
```
이 스크립트가 해 주는 일: `sitemap.xml`·`robots.txt`의 `{{SITE_URL}}` 교체, 모든 페이지에 canonical·og:url 삽입, og:image를 절대 주소로 교체, `{{CONTACT_EMAIL}}` 채우기(“자리표시자” 안내 문구도 삭제), `CNAME` 파일 작성.
- 이메일을 빼고 실행하면 `{{CONTACT_EMAIL}}`이 남아요. 나중에 `tools/set_domain.sh 도메인 이메일`로 다시 실행하면 돼요.
- 같은 변경을 소스 폴더(`/workspace/running-site`)에도 하려면 거기서 같은 명령을 실행하면 돼요.

## 3. GitHub Pages에서 도메인 연결
1. https://github.com/aucready/runwoori/settings/pages 에서 **Custom domain**에 `runwoori.com` 입력 → Save.
2. “DNS check successful”이 뜰 때까지 기다려요(몇 분~수십 분).
3. **Enforce HTTPS** 체크 (인증서가 만들어지면 활성화돼요. 최대 1시간 정도).
4. 확인: `https://runwoori.com/`, `/sitemap.xml`, `/robots.txt`, `/privacy.html`이 열리는지. `https://www.runwoori.com`은 자동으로 `runwoori.com`으로 넘어가요.

## 4. Google Search Console 등록
1. https://search.google.com/search-console 에서 **속성 추가** → “도메인” 유형에 `runwoori.com` 입력 → 안내된 TXT 레코드를 DNS에 추가 → 확인. (“URL 접두어”를 고르면 HTML 태그 방식도 가능해요.)
2. 왼쪽 **Sitemaps**에서 `sitemap.xml` 제출. 상태가 “성공”이면 정상이에요.
3. 상단 검사창에 홈과 글 몇 개의 주소를 넣고 **색인 생성 요청**을 눌러 두면 빨라져요.

## 5. AdSense 가입
1. https://adsense.google.com 에서 구글 계정으로 시작 → 사이트 주소 `runwoori.com`(https:// 없이) 입력, 국가 대한민국, 수익 받을 이름·주소·전화 확인.
2. 사이트 연결 방법으로 **AdSense 코드 스니펫**을 고르면 `ca-pub-숫자16자리`가 들어간 코드가 보여요. 그 숫자(게시자 ID)를 복사해요. 계정의 “내 계정 → 계정 정보”에서도 `pub-…` 형태로 확인돼요.
3. 아직 “확인” 버튼은 누르지 마세요. 먼저 6단계를 해요.

## 6. AdSense 코드 켜기 (`set_adsense.sh`)
```bash
cd /workspace/runwoori-deploy
tools/set_adsense.sh pub-1234567890123456     # 본인 게시자 ID
git add -A && git commit -m "AdSense 코드 활성화" && git push
```
- 모든 페이지 `<head>`의 주석 처리된 스크립트가 활성화되고 `ads.txt`가 `google.com, pub-…, DIRECT, f08c47fec0942fa0`으로 채워져요. (404 페이지는 오류 화면에 광고가 뜨지 않도록 일부러 뺐어요.)
- 1~2분 뒤 `https://runwoori.com/ads.txt`가 열리고, 페이지 소스에 `adsbygoogle.js`가 보이면 성공이에요.
- 되돌리려면 `tools/set_adsense.sh --off`.

## 7. 심사 요청과 대기
1. AdSense 화면으로 돌아가 “코드를 붙여넣었습니다” → **확인** → **검토 요청**.
2. 심사는 보통 며칠~몇 주 걸려요. 그동안 사이트 구조를 크게 바꾸지 않아요.
3. 승인되면 **자동 광고**를 켜거나 광고 단위를 만들어요. 결제 정보(주소 확인용 PIN, 세금 정보, 계좌)도 이때 입력해요.
4. 거절되면 사유(“가치가 별로 없는 콘텐츠”, “사이트 탐색 불편” 등)를 읽고 고쳐서 다시 요청해요. 글을 더 추가하는 게 가장 효과가 커요.

## 점검 목록
- [ ] 문의 이메일이 실제로 메일을 받을 수 있는 주소인가요?
- [ ] 홈·대회·가이드·소개·개인정보처리방침·이용약관·문의 페이지가 모두 열리나요?
- [ ] 모든 페이지 아래쪽에 소개·개인정보처리방침·이용약관·문의하기 링크가 보이나요?
- [ ] `sitemap.xml`이 Search Console에서 “성공”인가요?
- [ ] `ads.txt`가 `https://도메인/ads.txt`에서 열리나요?

## 글을 더 늘릴 때
가이드 글은 `/workspace/running-site-content/blog/`의 마크다운으로 관리해요. 새 글(`29-슬러그.md`)을 추가하고 아래를 실행해요.
```bash
python3 /workspace/running-site-content/tools/build_blog.py /workspace/running-site   # 글 JSON 생성
python3 /workspace/running-site/tools/build_sitemap.py                                  # sitemap에 반영
```
같은 결과물을 `/workspace/runwoori-deploy`에도 복사한 뒤 도메인이 이미 연결돼 있다면 `tools/set_domain.sh 도메인`을 다시 한 번 실행해 sitemap의 주소를 채워요.

## 참고
- 사이트 이름, 로고, 대회 데이터 업데이트(매일 새벽)는 그대로 유지돼요.
- 개인정보처리방침 시행일은 2026-11-01이에요. 광고를 켠 뒤 내용이 바뀌면 시행일도 함께 고쳐요.
