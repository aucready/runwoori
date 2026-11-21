import test from 'node:test';
import assert from 'node:assert/strict';
import {
  aggregateAvailability,
  assignSeats,
  buildIcs,
  dateTimeHeatmap,
  formatPace,
  googleCalendarUrl,
  leaderboard,
  mapLinks,
  promoteWaitlist,
  rankCombos,
  rateLimitDecision,
  rebalanceSeats,
  replyRoster,
  seatsLeft,
  splitCost,
} from '../src/logic.js';
import { validateCreate, validateExpenses, validateRecord, validateVotes } from '../src/validate.js';

const dates = [
  { id: 'd1', kind: 'date', label: '2026-11-28' },
  { id: 'd2', kind: 'date', label: '2026-12-05' },
];
const times = [
  { id: 't1', kind: 'time', label: '07:00' },
  { id: 't2', kind: 'time', label: '08:00' },
];
const courses = [
  { id: 'c1', kind: 'course', label: '여의나루' },
  { id: 'c2', kind: 'course', label: '반포' },
];

/** 가영·도윤·수아의 답, 답을 비운 하준, 취소한 사람. */
function samplePeople() {
  return [
    {
      id: 'p1', nickname: '가영', seat: 'voting', createdAt: '2026-11-01T00:00:01Z', responded: 1,
      votes: { d1: 2, d2: 0, t1: 2, t2: 1, c1: 2, c2: 0 },
    },
    {
      id: 'p2', nickname: '도윤', seat: 'voting', createdAt: '2026-11-01T00:00:02Z', responded: 1,
      votes: { d1: 1, d2: 2, t1: 1, t2: 2, c1: 1, c2: 2 },
    },
    {
      id: 'p3', nickname: '수아', seat: 'voting', createdAt: '2026-11-01T00:00:03Z', responded: 1,
      votes: { d1: 1, d2: 1, t1: 0, t2: 2, c1: 1, c2: 1 },
    },
    {
      id: 'p4', nickname: '하준', seat: 'voting', createdAt: '2026-11-01T00:00:04Z', responded: 0,
      votes: {},
    },
    {
      id: 'p5', nickname: '취소', seat: 'cancelled', createdAt: '2026-11-01T00:00:00Z', responded: 1,
      votes: { d1: 2, d2: 2, t1: 2, t2: 2, c1: 2, c2: 2 },
    },
  ];
}

test('가용 인원 집계: 가능·선호·불가·무응답을 나누고 취소한 사람은 빼요', () => {
  const rows = aggregateAvailability([...dates, ...times, ...courses], samplePeople());
  const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
  assert.equal(byId.d1.available, 3);
  assert.equal(byId.d1.prefer, 1);
  assert.equal(byId.d1.ok, 2);
  assert.deepEqual(byId.d1.names.prefer, ['가영']);
  assert.deepEqual(byId.d1.names.ok, ['도윤', '수아']);
  assert.equal(byId.d1.unanswered, 1);
  assert.deepEqual(byId.d1.names.unanswered, ['하준']);
  assert.equal(byId.t1.available, 2);
  assert.equal(byId.t1.no, 1);
  assert.deepEqual(byId.t1.names.no, ['수아']);
  assert.equal(byId.c2.available, 2);
  assert.ok(!rows.some((r) => r.names.ok.includes('취소') || r.names.prefer.includes('취소')));
});

test('베스트 조합: 가능한 사람 수가 먼저, 같으면 선호 점수, 그다음 날짜·시간·코스', () => {
  const ranked = rankCombos(dates, times, courses, samplePeople());
  assert.equal(ranked[0].available, 3);
  assert.equal(ranked[0].preference, 13);
  assert.deepEqual(
    [ranked[0].dateId, ranked[0].timeId, ranked[0].courseId],
    ['d1', 't2', 'c1'],
  );
  assert.deepEqual(ranked[0].nicknames, ['가영', '도윤', '수아']);
  // 2명으로 묶이는 조합 중 선호 합이 가장 큰 12월 5일 08:00 반포가 다음이다.
  assert.equal(ranked[1].available, 2);
  assert.equal(ranked[1].preference, 10);
  assert.deepEqual([ranked[1].dateLabel, ranked[1].timeLabel, ranked[1].courseLabel], ['2026-12-05', '08:00', '반포']);
  assert.ok(ranked.every((row, i) => i === 0 || ranked[i - 1].available > row.available ||
    (ranked[i - 1].available === row.available && ranked[i - 1].preference >= row.preference)));
  assert.ok(!ranked[0].nicknames.includes('하준'));
  assert.ok(!ranked[0].nicknames.includes('취소'));
});

test('가능한 인원이 같으면 선호(좋아요)가 많은 조합을 위로 올려요', () => {
  const people = [
    { id: 'a', nickname: '민지', seat: 'voting', votes: { d1: 1, t1: 1, c1: 1, d2: 2, t2: 2, c2: 2 } },
    { id: 'b', nickname: '우진', seat: 'voting', votes: { d1: 1, t1: 1, c1: 1, d2: 2, t2: 2, c2: 2 } },
  ];
  const ranked = rankCombos(dates, times, courses, people);
  const top = ranked[0];
  const other = ranked.find((r) => r.dateId === 'd1' && r.timeId === 't1' && r.courseId === 'c1');
  assert.equal(top.available, 2);
  assert.equal(other.available, 2);
  assert.deepEqual([top.dateId, top.timeId, top.courseId], ['d2', 't2', 'c2']);
  assert.ok(top.preference > other.preference);
});

test('인원과 선호가 같으면 더 이른 날짜, 이른 시간, 코스 이름 순이에요', () => {
  const people = [
    { id: 'a', nickname: '민지', seat: 'voting', votes: { d1: 1, d2: 1, t1: 1, t2: 1, c1: 1, c2: 1 } },
  ];
  const ranked = rankCombos(dates, times, courses, people);
  assert.deepEqual(
    ranked.map((r) => `${r.dateLabel} ${r.timeLabel} ${r.courseLabel}`),
    [
      '2026-11-28 07:00 반포',
      '2026-11-28 07:00 여의나루',
      '2026-11-28 08:00 반포',
      '2026-11-28 08:00 여의나루',
      '2026-12-05 07:00 반포',
      '2026-12-05 07:00 여의나루',
      '2026-12-05 08:00 반포',
      '2026-12-05 08:00 여의나루',
    ],
  );
});

test('히트맵 칸은 그 날짜·시간에 가장 많이 모이는 코스 인원이에요', () => {
  const heat = dateTimeHeatmap(dates, times, courses, samplePeople());
  const sat = heat[0];
  assert.equal(sat.cells.find((c) => c.timeId === 't2').available, 3);
  assert.equal(sat.cells.find((c) => c.timeId === 't2').courseLabel, '여의나루');
  assert.equal(sat.cells.find((c) => c.timeId === 't1').available, 2);
});

test('대기자 승급: 취소로 빈 자리가 생기면 먼저 기다린 사람만 올라가요', () => {
  const waitlist = [
    { id: 'b', nickname: '비', createdAt: '2026-11-02T00:00:00Z' },
    { id: 'a', nickname: '에이', createdAt: '2026-11-01T00:00:00Z' },
    { id: 'c', nickname: '씨', createdAt: '2026-11-03T00:00:00Z' },
  ];
  // 정원 4명, 참가 4명에서 한 명이 빠지면 대기 1명만 승급.
  const one = promoteWaitlist({ goingCount: 3, maxHeadcount: 4, waitlist });
  assert.deepEqual(one.map((p) => p.nickname), ['에이']);

  const two = promoteWaitlist({ goingCount: 2, maxHeadcount: 4, waitlist });
  assert.deepEqual(two.map((p) => p.nickname), ['에이', '비']);

  const full = promoteWaitlist({ goingCount: 4, maxHeadcount: 4, waitlist });
  assert.deepEqual(full, []);

  const unlimited = promoteWaitlist({ goingCount: 1, maxHeadcount: null, waitlist });
  assert.deepEqual(unlimited, []);
});

test('확정 자리: 먼저 들어온 사람이 정원을 채우고 나머지는 대기예요', () => {
  const eligible = [
    { id: '3', nickname: '셋', createdAt: '2026-11-03T00:00:00Z' },
    { id: '1', nickname: '하나', createdAt: '2026-11-01T00:00:00Z' },
    { id: '2', nickname: '둘', createdAt: '2026-11-02T00:00:00Z' },
  ];
  const capped = assignSeats(eligible, 2);
  assert.deepEqual(capped.going.map((p) => p.nickname), ['하나', '둘']);
  assert.deepEqual(capped.waitlist.map((p) => p.nickname), ['셋']);

  const open = assignSeats(eligible, null);
  assert.equal(open.going.length, 3);
  assert.equal(open.waitlist.length, 0);
});

test('정원을 줄이면 늦게 온 참가자가 대기로 내려가요', () => {
  const going = [
    { id: '1', nickname: '하나', createdAt: '2026-11-01T00:00:00Z' },
    { id: '2', nickname: '둘', createdAt: '2026-11-02T00:00:00Z' },
  ];
  const waitlist = [{ id: '3', nickname: '셋', createdAt: '2026-11-03T00:00:00Z' }];
  const down = rebalanceSeats({ going, waitlist, maxHeadcount: 1 });
  assert.deepEqual(down.going.map((p) => p.nickname), ['하나']);
  assert.deepEqual(down.waitlist.map((p) => p.nickname), ['둘', '셋']);

  const up = rebalanceSeats({ going, waitlist, maxHeadcount: null });
  assert.deepEqual(up.going.map((p) => p.nickname), ['하나', '둘', '셋']);
  assert.equal(up.waitlist.length, 0);
  assert.equal(seatsLeft(4, 3), 1);
  assert.equal(seatsLeft(null, 3), null);
});

test('정산: 총액을 참가 인원으로 나누고 나머지는 원 단위로 남겨요', () => {
  const items = [
    { label: '뒤풀이', amount: 45000 },
    { label: '간식', amount: 12000 },
    { label: '장소비', amount: 3000 },
  ];
  const even = splitCost(items, 4);
  assert.equal(even.total, 60000);
  assert.equal(even.perPerson, 15000);
  assert.equal(even.remainder, 0);
  assert.equal(even.lines.length, 3);

  const odd = splitCost([{ label: '간식', amount: 10000 }], 3);
  assert.equal(odd.perPerson, 3333);
  assert.equal(odd.remainder, 1);
  assert.equal(odd.perPerson * 3 + odd.remainder, 10000);

  const seven = splitCost(items, 7);
  assert.equal(seven.perPerson, 8571);
  assert.equal(seven.remainder, 3);
  assert.equal(seven.perPerson * 7 + seven.remainder, 60000);

  const nobody = splitCost(items, 0);
  assert.equal(nobody.perPerson, null);
  assert.equal(nobody.remainder, 60000);
});

test('기록 페이스와 리더보드는 1km당 시간이 빠른 순이에요', () => {
  assert.equal(formatPace(360), `6'00"`);
  assert.equal(formatPace(305.4), `5'05"`);
  const board = leaderboard([
    { nickname: '느림', distanceKm: 5, durationSec: 40 * 60 },
    { nickname: '빠름', distanceKm: 10, durationSec: 50 * 60 },
    { nickname: '중간', distanceKm: 8, durationSec: 48 * 60 },
  ]);
  assert.deepEqual(board.map((r) => r.nickname), ['빠름', '중간', '느림']);
  assert.equal(board[0].pace, `5'00"`);
});

test('답변 명단: 예상 이름과 실제 닉네임을 맞춰 답함·미답·참가만을 나눠요', () => {
  const roster = replyRoster(['가영', '하준', '없는분'], samplePeople());
  assert.deepEqual(roster.expected.map((r) => [r.name, r.status]), [
    ['가영', 'replied'],
    ['하준', 'joined'],
    ['없는분', 'missing'],
  ]);
  assert.deepEqual(roster.others.map((r) => r.nickname).sort(), ['도윤', '수아']);
});

test('지도 링크와 캘린더', () => {
  const maps = mapLinks('여의도한강공원 여의나루');
  assert.match(maps.naver, /^https:\/\/map\.naver\.com\/p\/search\//);
  assert.match(maps.kakao, /^https:\/\/map\.kakao\.com\/link\/search\//);
  assert.match(maps.google, /^https:\/\/www\.google\.com\/maps\/search\/\?api=1&query=/);
  assert.match(decodeURIComponent(maps.google), /여의도한강공원 여의나루/);

  const gcal = googleCalendarUrl({
    title: '토요일 아침 한강',
    date: '2026-11-28',
    time: '07:00',
    location: '여의나루',
    details: '크루 러닝',
  });
  const u = new URL(gcal);
  assert.equal(u.searchParams.get('ctz'), 'Asia/Seoul');
  assert.equal(u.searchParams.get('dates'), '20261128T070000/20261128T090000');

  const ics = buildIcs({
    id: 'run1',
    title: '한강, 아침',
    date: '2026-11-28',
    time: '23:30',
    location: '여의나루',
    details: '줄\n바꿈',
    stamp: '20261121T000000Z',
  });
  assert.match(ics, /DTSTART;TZID=Asia\/Seoul:20261128T233000/);
  assert.match(ics, /DTEND;TZID=Asia\/Seoul:20261129T013000/);
  assert.match(ics, /SUMMARY:한강\\, 아침/);
  assert.match(ics, /DESCRIPTION:줄\\n바꿈/);
});

test('생성 횟수 제한: 창 안에서는 한도에서 멈추고, 창이 지나면 다시 1부터', () => {
  const first = rateLimitDecision({ count: 0, windowStart: null, now: 1_000, limit: 2, windowMs: 100 });
  assert.equal(first.allowed, true);
  assert.equal(first.count, 1);
  const second = rateLimitDecision({ count: 1, windowStart: 1_000, now: 1_050, limit: 2, windowMs: 100 });
  assert.equal(second.allowed, true);
  assert.equal(second.count, 2);
  const blocked = rateLimitDecision({ count: 2, windowStart: 1_000, now: 1_080, limit: 2, windowMs: 100 });
  assert.equal(blocked.allowed, false);
  assert.equal(blocked.count, 2);
  assert.equal(blocked.retryAfterSec, 1);
  const reset = rateLimitDecision({ count: 2, windowStart: 1_000, now: 1_100, limit: 2, windowMs: 100 });
  assert.equal(reset.allowed, true);
  assert.equal(reset.count, 1);
  assert.equal(reset.windowStart, 1_100);
});

test('입력 검사: 과거 날짜, 중복 시간, 금액, 기록', () => {
  const badDate = validateCreate({
    title: '아침 러닝',
    hostNickname: '민지',
    dates: ['2026-11-01'],
    times: ['07:00'],
    courses: [{ name: '여의나루', place: '여의도한강공원' }],
  }, '2026-11-21');
  assert.equal(badDate.ok, false);

  const dup = validateCreate({
    title: '아침 러닝',
    hostNickname: '민지',
    dates: ['2026-11-28'],
    times: ['07:00', '07:00'],
    courses: [{ name: '여의나루', place: '여의도한강공원' }],
  }, '2026-11-21');
  assert.equal(dup.ok, false);

  const ok = validateCreate({
    title: '  토요일 아침  ',
    hostNickname: ' 민지 ',
    memo: '가볍게',
    dates: ['2026-11-28', '2026-12-05'],
    times: ['07:00'],
    courses: [{ name: '여의나루', place: '여의도한강공원 여의나루역' }],
    maxHeadcount: 6,
    openJoin: true,
    expectedNames: '민지\n우진\n민지',
  }, '2026-11-21');
  assert.equal(ok.ok, true);
  assert.equal(ok.value.title, '토요일 아침');
  assert.equal(ok.value.hostNickname, '민지');
  assert.deepEqual(ok.value.expectedNames, ['민지', '우진']);
  assert.equal(ok.value.maxHeadcount, 6);

  assert.equal(validateExpenses({ items: [{ label: '간식', amount: 10.5 }] }).ok, false);
  assert.equal(validateExpenses({ items: [{ label: '간식', amount: 1500 }] }).ok, true);
  assert.equal(validateRecord({ distanceKm: 10.25, durationSec: 3600, memo: '바람' }).ok, true);
  assert.equal(validateRecord({ distanceKm: 10.256, durationSec: 3600 }).ok, false);
  assert.equal(validateVotes({ votes: [{ optionId: 'd1', state: 1 }] }, ['d1', 't1']).ok, false);
  assert.equal(validateVotes({
    votes: [{ optionId: 'd1', state: 2 }, { optionId: 't1', state: 0 }],
  }, ['d1', 't1']).ok, true);
});
