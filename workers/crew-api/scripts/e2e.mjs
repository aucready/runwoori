/**
 * 로컬 wrangler dev 에 대한 흐름 확인.
 *   node scripts/e2e.mjs
 * API가 http://127.0.0.1:8787 에 떠 있어야 합니다.
 */
const API = process.env.CREW_API || 'http://127.0.0.1:8787';
const ORIGIN = 'http://127.0.0.1:8080';

function seoulToday() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
}
function addDays(iso, days) {
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  const p = (n) => String(n).padStart(2, '0');
  return `${dt.getUTCFullYear()}-${p(dt.getUTCMonth() + 1)}-${p(dt.getUTCDate())}`;
}

async function api(path, opt = {}) {
  const headers = { accept: 'application/json', origin: ORIGIN, ...(opt.headers || {}) };
  if (opt.body != null) headers['content-type'] = 'application/json';
  const res = await fetch(API + path, {
    method: opt.method || 'GET',
    headers,
    body: opt.body != null ? JSON.stringify(opt.body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const err = new Error(`${opt.method || 'GET'} ${path} → ${res.status} ${typeof data === 'string' ? data : data?.error || text}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function votesFor(options, pick) {
  return options.map((o) => ({ optionId: o.id, state: pick(o) }));
}

const today = seoulToday();
const d1 = addDays(today, 7);
const d2 = addDays(today, 14);
const created = await api('/v1/runs', {
  method: 'POST',
  body: {
    title: '토요일 아침 한강 크루',
    hostNickname: '민지',
    memo: '10km 안쪽, 비 오면 다음 주로 미뤄요.',
    dates: [d1, d2],
    times: ['07:00', '08:00'],
    courses: [
      { name: '여의나루', place: '여의도한강공원 여의나루역 2번 출구' },
      { name: '반포한강공원', place: '반포한강공원 잠수교 남단' },
    ],
    maxHeadcount: 3,
    openJoin: true,
    expectedNames: ['민지', '가영', '도윤', '수아', '하준'],
  },
});

const hostHeaders = { 'x-host-key': created.hostKey };
const pub = await api('/v1/runs/' + created.id);
const by = (kind, label) => pub.options.find((o) => o.kind === kind && o.label === label);

async function join(nickname, pick) {
  const res = await api(`/v1/runs/${created.id}/participants`, { method: 'POST', body: { nickname } });
  const fresh = await api('/v1/runs/' + created.id);
  await api(`/v1/runs/${created.id}/votes`, {
    method: 'PUT',
    headers: { 'x-participant-token': res.token },
    body: { votes: votesFor(fresh.options, pick) },
  });
  return res;
}

// 민지는 만들 때 참가자로 들어가 있어요.
await api(`/v1/runs/${created.id}/votes`, {
  method: 'PUT',
  headers: { 'x-participant-token': created.participantToken },
  body: {
    votes: votesFor(pub.options, (o) => {
      if (o.label === d1 || o.label === '07:00' || o.label === '여의나루') return 2;
      return 1;
    }),
  },
});
const gayoung = await join('가영', (o) => (o.label === d1 || o.label === '08:00' || o.label === '여의나루' ? 2 : o.label === '07:00' ? 1 : 0));
const doyun = await join('도윤', (o) => (o.label === d2 || o.label === '08:00' || o.label === '반포한강공원' ? 2 : 1));
const sua = await join('수아', (o) => (o.label === '07:00' ? 0 : 1));

const host = await api('/v1/runs/' + created.id + '/host', { headers: hostHeaders });
const top = host.recommendation[0];
if (!top || top.available < 2) throw new Error('추천 조합이 비어 있어요: ' + JSON.stringify(host.recommendation[0]));
const replied = host.roster.expected.filter((r) => r.status === 'replied').map((r) => r.name).sort();
const missing = host.roster.expected.filter((r) => r.status === 'missing').map((r) => r.name);
if (!replied.includes('민지') || !replied.includes('가영') || missing.join() !== '하준') {
  throw new Error('답변 명단이 예상과 달라요 ' + JSON.stringify(host.roster.expected));
}

await api('/v1/runs/' + created.id + '/confirm', {
  method: 'POST',
  headers: hostHeaders,
  body: { dateId: top.dateId, timeId: top.timeId, courseId: top.courseId, maxHeadcount: 3, openJoin: true },
});
let after = await api('/v1/runs/' + created.id);
if (after.status !== 'confirmed') throw new Error('확정되지 않았어요');
if (after.counts.going !== 3) throw new Error('참가 인원 ' + after.counts.going);
if (after.counts.waitlist !== 1) throw new Error('대기 인원 ' + after.counts.waitlist + ' (정원 3, 가능 인원 4를 기대)');
if (after.seatsLeft !== 0) throw new Error('잔여 자리 ' + after.seatsLeft);

const open = await api(`/v1/runs/${created.id}/participants`, { method: 'POST', body: { nickname: '우진' } });
if (open.participant.seat !== 'waitlist') throw new Error('빈자리 없을 때 대기가 아니에요: ' + open.participant.seat);

// 참가 중인 사람 한 명이 빠지면 대기 1순위가 올라온다.
const goingBefore = (await api('/v1/runs/' + created.id + '/host', { headers: hostHeaders })).participants.filter((p) => p.seat === 'going');
const canceller = goingBefore[goingBefore.length - 1];
const cancelToken = { 민지: created.participantToken, 가영: gayoung.token, 도윤: doyun.token, 수아: sua.token }[canceller.nickname];
const cancelled = await api(`/v1/runs/${created.id}/cancel`, {
  method: 'POST',
  headers: { 'x-participant-token': cancelToken },
});
if (!cancelled.promoted) throw new Error('대기 승급이 없어요');
after = await api('/v1/runs/' + created.id);
if (after.counts.going !== 3) throw new Error('승급 후 참가 ' + after.counts.going);
if (!after.goingNames.includes(cancelled.promoted)) throw new Error('승급된 이름이 참가 명단에 없어요');

await api(`/v1/runs/${created.id}/expenses`, {
  method: 'PUT',
  headers: hostHeaders,
  body: { items: [{ label: '뒤풀이', amount: 45000 }, { label: '간식', amount: 12000 }, { label: '장소비', amount: 3000 }] },
});
after = await api('/v1/runs/' + created.id);
if (after.expenses.split.total !== 60000) throw new Error('정산 합계');
if (after.expenses.split.perPerson !== 20000 || after.expenses.split.remainder !== 0) {
  throw new Error('3명 정산 ' + JSON.stringify(after.expenses.split));
}

const runner = after.goingNames[0];
const runnerToken = { 민지: created.participantToken, 가영: gayoung.token, 도윤: doyun.token, 수아: sua.token, 우진: open.token }[runner];
await api(`/v1/runs/${created.id}/record`, {
  method: 'PUT',
  headers: { 'x-participant-token': runnerToken },
  body: { distanceKm: 10, durationSec: 50 * 60, memo: '바람 맞으며 여유롭게' },
});
const second = after.goingNames[1];
const secondToken = { 민지: created.participantToken, 가영: gayoung.token, 도윤: doyun.token, 수아: sua.token, 우진: open.token }[second];
await api(`/v1/runs/${created.id}/record`, {
  method: 'PUT',
  headers: { 'x-participant-token': secondToken },
  body: { distanceKm: 8.2, durationSec: 48 * 60, memo: '' },
});
after = await api('/v1/runs/' + created.id);
if (after.records[0].pace !== `5'00"`) throw new Error('페이스 ' + after.records[0].pace);
if (!after.confirmed.calendar.ics.endsWith('/event.ics')) throw new Error('ics 주소');
if (!after.confirmed.maps.naver.includes('map.naver.com')) throw new Error('네이버 지도');
const ics = await fetch(after.confirmed.calendar.ics);
if (!ics.ok || !(await ics.text()).includes('DTSTART;TZID=Asia/Seoul')) throw new Error('ics 본문');
const share = await fetch(`${API}/share/${created.id}`);
const shareHtml = await share.text();
if (!share.ok || !shareHtml.includes('og:title') || !shareHtml.includes(created.id) && !shareHtml.includes('토요일')) {
  throw new Error('공유 페이지 OG');
}
if (!shareHtml.includes('토요일 아침 한강 크루')) throw new Error('OG 제목에 약속 이름이 없어요');

const bad = await fetch(API + '/v1/runs', {
  method: 'POST',
  headers: { 'content-type': 'application/json', origin: 'https://evil.example' },
  body: '{}',
});
if (bad.status !== 403) throw new Error('CORS 차단이 아니에요 ' + bad.status);

console.log(JSON.stringify({
  id: created.id,
  hostKey: created.hostKey,
  participantToken: created.participantToken,
  tokens: {
    민지: created.participantToken,
    가영: gayoung.token,
    도윤: doyun.token,
    수아: sua.token,
    우진: open.token,
  },
  top,
  going: after.goingNames,
  waitlist: after.counts.waitlist,
  promoted: cancelled.promoted,
  perPerson: after.expenses.split.perPerson,
  pace: after.records[0].pace,
  share: `${API}/share/${created.id}`,
}, null, 2));
