# 크루 러닝 약속 API

Run우리(`/crew/`)의 서버예요. GitHub Pages는 정적 사이트라서, 약속·투표·대기·정산은 Cloudflare Worker와 D1(SQLite)에 둡니다. 계정은 없고, 추측하기 어려운 링크와 호스트 열쇠만 사용해요. 열쇠 원문은 저장하지 않고 SHA-256 해시만 저장합니다.

이 저장소의 에이전트는 워커를 **배포하지 않아요.** 아래 순서는 저장소 주인이 직접 실행합니다.

## 로컬에서 확인

저장소 루트와 이 폴더, 두 곳에서 서버가 필요해요.

```bash
cd workers/crew-api
npm install
npx wrangler d1 migrations apply runwoori-crew --local
npx wrangler dev --local --port 8787
```

다른 터미널에서 정적 사이트:

```bash
# 저장소 루트
python3 -m http.server 8080
```

브라우저에서 <http://127.0.0.1:8080/crew/index.html> 을 엽니다. `crew/config.js`의 `CREW_API_BASE`가 비어 있으면, localhost로 연 페이지만 `http://127.0.0.1:8787` 을 찾습니다. runwoori.com 에서는 비어 있는 동안 "준비 중"으로 안내해요.

단위 테스트(가용 인원, 조합 순위, 대기 승급, 정산):

```bash
npm test
```

API가 8787에서 떠 있을 때 만들기부터 확정, 대기 승급, 정산, 기록까지 한 번에 확인하려면 `node scripts/e2e.mjs` 를 실행해요.

로컬에서 공유 링크(`/share/:id`)가 정적 페이지로 돌아가게 하려면 `wrangler.toml`의 `SITE_ORIGIN`을 `http://127.0.0.1:8080` 으로 잠시 바꾸거나, `npx wrangler dev --local --port 8787 --var SITE_ORIGIN:http://127.0.0.1:8080` 처럼 덮어쓰면 됩니다. 배포용 기본값은 `https://runwoori.com` 이에요.

## 배포

1. Cloudflare에 로그인합니다.

   ```bash
   npx wrangler login
   ```

2. D1 데이터베이스를 만듭니다.

   ```bash
   npx wrangler d1 create runwoori-crew
   ```

3. 출력된 `database_id`를 `wrangler.toml`의 `database_id`에 넣습니다. 지금 들어 있는 `00000000-0000-0000-0000-000000000000` 은 자리표시자라 원격 배포에 쓸 수 없어요.

4. 마이그레이션을 원격에 적용합니다.

   ```bash
   npx wrangler d1 migrations apply runwoori-crew --remote
   ```

5. 워커를 배포합니다.

   ```bash
   npx wrangler deploy
   ```

   끝나면 `https://runwoori-crew-api.<계정>.workers.dev` 같은 주소가 나와요. 커스텀 도메인을 붙이려면 Cloudflare 대시보드에서 이 워커에 라우트를 추가하면 됩니다.

6. 사이트 설정을 바꿉니다. `crew/config.js`의 **이 상수만** 배포된 주소로 적어요.

   ```js
   const CREW_API_BASE = 'https://runwoori-crew-api.<계정>.workers.dev';
   ```

   끝에 슬래시는 붙이지 마세요. 커밋하고 GitHub Pages에 푸시하면 크루 페이지가 그 API를 호출합니다.

7. 동작 확인: `https://<워커>/health` 가 `{"ok":true}` 를 돌려주고, runwoori.com/crew/ 에서 약속을 만든 뒤 참가 링크를 카카오톡에 붙여 제목 미리보기가 보이는지 봅니다.

## 주소

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/health` | 살아 있는지 |
| GET | `/share/:id` | 카카오톡용 OG가 있는 공유 페이지. 사람은 `/crew/r.html`로 이동 |
| POST | `/v1/runs` | 약속 만들기. 응답의 `hostKey`는 이 때 한 번만 줍니다 |
| GET | `/v1/runs/:id` | 참가자에게 보이는 내용 |
| POST | `/v1/runs/:id/participants` | 닉네임으로 참가 |
| PUT | `/v1/runs/:id/votes` | 날짜·시간·코스 선택 |
| POST | `/v1/runs/:id/cancel` | 참가 취소. 대기 1순위가 올라옵니다 |
| PUT | `/v1/runs/:id/record` | 거리·시간·메모 |
| GET | `/v1/runs/:id/event.ics` | 확정된 일정 파일 |
| GET | `/v1/runs/:id/host` | 호스트 화면. 헤더 `X-Host-Key` |
| POST | `/v1/runs/:id/confirm` | 날짜 확정 |
| POST | `/v1/runs/:id/done` | 완료 |
| PUT | `/v1/runs/:id/expenses` | 정산 항목 |
| DELETE | `/v1/runs/:id` | 약속 삭제 |

CORS는 `https://runwoori.com`과 `http://localhost`, `http://127.0.0.1`(모든 포트)만 허용해요. 브라우저에 비밀 키를 넣지 않아요. 약속 생성은 IP 해시 기준으로 한 시간에 5번까지예요. IP 원문은 저장하지 않아요.

상태 흐름은 `모집중 → 날짜확정 → 완료` 입니다.
