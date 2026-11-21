/**
 * 요청 본문 검사. 통과하면 저장에 쓸 값만 돌려주고, 아니면 { error } 를 돌려준다.
 */
import { addDaysISO, nicknameKey, normalizeNickname } from './logic.js';

export const LIMITS = {
  title: 40,
  memo: 400,
  nickname: 16,
  dates: 8,
  times: 8,
  courses: 6,
  courseName: 40,
  place: 80,
  expected: 30,
  headcount: 200,
  expenses: 12,
  expenseLabel: 30,
  expenseAmount: 1_000_000,
  distanceMin: 0.1,
  distanceMax: 300,
  durationMin: 30,
  durationMax: 86_400,
  recordMemo: 200,
  participants: 200,
  horizonDays: 366,
};

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

function fail(error) {
  return { ok: false, error };
}

export function validNickname(raw) {
  const s = normalizeNickname(raw);
  if (s.length < 1 || s.length > LIMITS.nickname) return false;
  if (!/^[0-9A-Za-z가-힣][0-9A-Za-z가-힣. ]*$/.test(s)) return false;
  return true;
}

function cleanLine(raw, max) {
  return String(raw ?? '').replace(/[\u0000-\u001F\u007F]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, max);
}

function isRealDate(iso) {
  if (!DATE_RE.test(iso)) return false;
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

function unique(list) {
  return new Set(list).size === list.length;
}

export function parseHeadcount(value) {
  if (value == null || value === '') return { ok: true, value: null };
  if (typeof value === 'boolean' || typeof value === 'object') return fail('정원은 숫자로 적어 주세요.');
  const n = typeof value === 'number' ? value : Number(String(value).trim());
  if (!Number.isInteger(n) || n < 1 || n > LIMITS.headcount) {
    return fail(`정원은 1명에서 ${LIMITS.headcount}명 사이로 적어 주세요.`);
  }
  return { ok: true, value: n };
}

function parseOptions(body, today) {
  if (!Array.isArray(body.dates) || body.dates.length < 1 || body.dates.length > LIMITS.dates) {
    return fail(`날짜 후보는 1개에서 ${LIMITS.dates}개까지 넣을 수 있어요.`);
  }
  if (!Array.isArray(body.times) || body.times.length < 1 || body.times.length > LIMITS.times) {
    return fail(`출발 시간은 1개에서 ${LIMITS.times}개까지 넣을 수 있어요.`);
  }
  if (!Array.isArray(body.courses) || body.courses.length < 1 || body.courses.length > LIMITS.courses) {
    return fail(`코스는 1곳에서 ${LIMITS.courses}곳까지 넣을 수 있어요.`);
  }
  const until = addDaysISO(today, LIMITS.horizonDays);
  const dates = [];
  for (const raw of body.dates) {
    const iso = String(raw || '').trim();
    if (!isRealDate(iso)) return fail('날짜는 2026-11-28 처럼 적어 주세요.');
    if (iso < today || iso > until) return fail('날짜는 오늘부터 1년 안으로 골라 주세요.');
    dates.push(iso);
  }
  if (!unique(dates)) return fail('같은 날짜가 두 번 들어 있어요.');
  const times = [];
  for (const raw of body.times) {
    const t = String(raw || '').trim();
    if (!TIME_RE.test(t)) return fail('출발 시간은 07:00 처럼 적어 주세요.');
    times.push(t);
  }
  if (!unique(times)) return fail('같은 출발 시간이 두 번 들어 있어요.');
  const courses = [];
  for (const raw of body.courses) {
    const name = cleanLine(raw?.name, LIMITS.courseName);
    const place = cleanLine(raw?.place, LIMITS.place);
    if (name.length < 1) return fail('코스 이름을 적어 주세요.');
    if (place.length < 2) return fail('집결지는 지도에서 찾을 수 있게 두 글자 이상 적어 주세요.');
    courses.push({ name, place });
  }
  if (!unique(courses.map((c) => c.name))) return fail('같은 코스 이름이 두 번 들어 있어요.');
  return { ok: true, dates, times, courses };
}

export function validateCreate(body, today) {
  if (!body || typeof body !== 'object') return fail('내용을 읽어 주세요.');
  const title = cleanLine(body.title, LIMITS.title);
  if (title.length < 1) return fail('약속 이름을 적어 주세요.');
  if (!validNickname(body.hostNickname)) return fail('닉네임은 1~16자의 한글, 영문, 숫자로 적어 주세요.');
  const hostNickname = normalizeNickname(body.hostNickname);
  const memo = cleanLine(body.memo, LIMITS.memo);
  const opts = parseOptions(body, today);
  if (!opts.ok) return opts;
  const cap = parseHeadcount(body.maxHeadcount);
  if (!cap.ok) return cap;
  const openJoin = Boolean(body.openJoin);
  const names = parseExpected(body.expectedNames);
  if (!names.ok) return names;
  return {
    ok: true,
    value: {
      title,
      hostNickname,
      memo,
      dates: opts.dates,
      times: opts.times,
      courses: opts.courses,
      maxHeadcount: cap.value,
      openJoin: openJoin && cap.value != null ? true : openJoin,
      expectedNames: names.value,
    },
  };
}

function parseExpected(raw) {
  if (raw == null || raw === '') return { ok: true, value: [] };
  const list = Array.isArray(raw) ? raw : String(raw).split(/[\n,]/);
  const names = [];
  const seen = new Set();
  for (const item of list) {
    const name = normalizeNickname(item);
    if (!name) continue;
    if (!validNickname(name)) return fail('크루 이름은 닉네임과 같이 1~16자로 적어 주세요.');
    const key = nicknameKey(name);
    if (seen.has(key)) continue;
    seen.add(key);
    names.push(name);
    if (names.length > LIMITS.expected) return fail(`예상 인원은 ${LIMITS.expected}명까지 적을 수 있어요.`);
  }
  return { ok: true, value: names };
}

export function validatePatch(body) {
  if (!body || typeof body !== 'object') return fail('내용을 읽어 주세요.');
  const value = {};
  if (body.title != null) {
    const title = cleanLine(body.title, LIMITS.title);
    if (title.length < 1) return fail('약속 이름을 적어 주세요.');
    value.title = title;
  }
  if (body.memo != null) value.memo = cleanLine(body.memo, LIMITS.memo);
  if (body.maxHeadcount !== undefined) {
    const cap = parseHeadcount(body.maxHeadcount);
    if (!cap.ok) return cap;
    value.maxHeadcount = cap.value;
  }
  if (body.openJoin != null) value.openJoin = Boolean(body.openJoin);
  if (body.expectedNames != null) {
    const names = parseExpected(body.expectedNames);
    if (!names.ok) return names;
    value.expectedNames = names.value;
  }
  if (!Object.keys(value).length) return fail('바꿀 내용이 없어요.');
  return { ok: true, value };
}

export function validateVotes(body, optionIds) {
  if (!body || !Array.isArray(body.votes)) return fail('선택한 답을 읽어 주세요.');
  const allowed = new Set(optionIds);
  if (body.votes.length !== allowed.size) return fail('날짜, 출발 시간, 코스를 모두 골라 주세요.');
  const votes = {};
  for (const row of body.votes) {
    const id = String(row?.optionId || '');
    if (!allowed.has(id) || votes[id] != null) return fail('선택지가 맞지 않아요. 새로고침 후 다시 골라 주세요.');
    const state = row.state;
    if (state !== 0 && state !== 1 && state !== 2) return fail('각 후보는 어려워요, 괜찮아요, 좋아요 중 하나로 골라 주세요.');
    votes[id] = state;
  }
  return { ok: true, value: votes };
}

export function validateExpenses(body) {
  if (!body || !Array.isArray(body.items)) return fail('정산 항목을 읽어 주세요.');
  if (body.items.length > LIMITS.expenses) return fail(`정산 항목은 ${LIMITS.expenses}개까지 넣을 수 있어요.`);
  const items = [];
  for (const raw of body.items) {
    const label = cleanLine(raw?.label, LIMITS.expenseLabel);
    if (!label) return fail('정산 이름을 적어 주세요. 예: 뒤풀이, 간식, 장소비');
    const amount = raw?.amount;
    if (!Number.isInteger(amount) || amount < 0 || amount > LIMITS.expenseAmount) {
      return fail('금액은 0원에서 100만원 사이의 정수로 적어 주세요.');
    }
    items.push({ label, amount });
  }
  return { ok: true, value: items };
}

export function validateRecord(body) {
  if (!body || typeof body !== 'object') return fail('기록을 읽어 주세요.');
  const distanceKm = typeof body.distanceKm === 'number' ? body.distanceKm : Number(body.distanceKm);
  if (!Number.isFinite(distanceKm) || distanceKm < LIMITS.distanceMin || distanceKm > LIMITS.distanceMax) {
    return fail('거리는 0.1km에서 300km 사이로 적어 주세요.');
  }
  const decimals = String(distanceKm).includes('.') ? String(distanceKm).split('.')[1].length : 0;
  if (decimals > 2) return fail('거리는 소수점 둘째 자리까지 적어 주세요.');
  const durationSec = typeof body.durationSec === 'number' ? body.durationSec : Number(body.durationSec);
  if (!Number.isInteger(durationSec) || durationSec < LIMITS.durationMin || durationSec > LIMITS.durationMax) {
    return fail('시간은 30초에서 24시간 사이로 적어 주세요.');
  }
  const memo = cleanLine(body.memo, LIMITS.recordMemo);
  return {
    ok: true,
    value: { distanceKm: Math.round(distanceKm * 100) / 100, durationSec, memo },
  };
}

export function validateConfirm(body, options) {
  if (!body || typeof body !== 'object') return fail('확정할 조합을 골라 주세요.');
  const date = (options || []).find((o) => o.id === body.dateId && o.kind === 'date');
  const time = (options || []).find((o) => o.id === body.timeId && o.kind === 'time');
  const course = (options || []).find((o) => o.id === body.courseId && o.kind === 'course');
  if (!date || !time || !course) return fail('날짜, 출발 시간, 코스를 하나씩 골라 주세요.');
  return { ok: true, value: { date, time, course } };
}
