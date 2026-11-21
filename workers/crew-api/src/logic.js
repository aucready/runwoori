/**
 * 크루 러닝 약속의 순수 계산.
 * 가용 인원 집계, 날짜·시간·코스 조합 순위, 대기자 승급, 정산, 페이스.
 * DB나 요청 객체에 의존하지 않는다.
 */

export function byArrival(a, b) {
  return String(a.createdAt).localeCompare(String(b.createdAt)) || String(a.id).localeCompare(String(b.id));
}

export function normalizeNickname(raw) {
  return String(raw ?? '').replace(/[\u0000-\u001F\u007F]/g, '').trim().replace(/\s+/g, ' ');
}

export function nicknameKey(raw) {
  return normalizeNickname(raw).toLowerCase();
}

/** 0 불가 · 1 가능 · 2 선호. 답하지 않은 항목은 집계에서 빠진다. */
export function aggregateAvailability(options, participants) {
  const active = (participants || []).filter((p) => p.seat !== 'cancelled');
  return (options || []).map((o) => {
    let ok = 0;
    let prefer = 0;
    let no = 0;
    let unanswered = 0;
    const names = { prefer: [], ok: [], no: [], unanswered: [] };
    for (const p of active) {
      const s = p.votes ? p.votes[o.id] : undefined;
      if (s === 2) {
        prefer += 1;
        names.prefer.push(p.nickname);
      } else if (s === 1) {
        ok += 1;
        names.ok.push(p.nickname);
      } else if (s === 0) {
        no += 1;
        names.no.push(p.nickname);
      } else {
        unanswered += 1;
        names.unanswered.push(p.nickname);
      }
    }
    return {
      id: o.id,
      kind: o.kind,
      label: o.label,
      ok,
      prefer,
      no,
      unanswered,
      available: ok + prefer,
      names,
    };
  });
}

/**
 * 한 사람이 조합에 가능한 조건: 날짜·시간·코스를 모두 1 이상으로 골랐을 때.
 * 순위: 가능한 사람 수 → 선호 점수(가능 1, 선호 2의 합) → 날짜 → 시간 → 코스 이름.
 * 취소한 사람과 답을 비운 사람은 포함하지 않는다.
 */
export function rankCombos(dates, times, courses, participants) {
  const combos = [];
  for (const date of dates || []) {
    for (const time of times || []) {
      for (const course of courses || []) {
        const nicknames = [];
        let preference = 0;
        for (const p of participants || []) {
          if (p.seat === 'cancelled') continue;
          const dv = p.votes?.[date.id] ?? 0;
          const tv = p.votes?.[time.id] ?? 0;
          const cv = p.votes?.[course.id] ?? 0;
          if (dv >= 1 && tv >= 1 && cv >= 1) {
            nicknames.push(p.nickname);
            preference += dv + tv + cv;
          }
        }
        combos.push({
          dateId: date.id,
          timeId: time.id,
          courseId: course.id,
          dateLabel: date.label,
          timeLabel: time.label,
          courseLabel: course.label,
          available: nicknames.length,
          preference,
          nicknames,
        });
      }
    }
  }
  combos.sort((a, b) =>
    b.available - a.available ||
    b.preference - a.preference ||
    String(a.dateLabel).localeCompare(String(b.dateLabel)) ||
    String(a.timeLabel).localeCompare(String(b.timeLabel)) ||
    String(a.courseLabel).localeCompare(String(b.courseLabel), 'ko'));
  return combos;
}

/** 날짜×시간 칸은, 그 칸에서 가장 많은 사람이 모이는 코스의 인원이다. */
export function dateTimeHeatmap(dates, times, courses, participants) {
  return (dates || []).map((date) => ({
    dateId: date.id,
    label: date.label,
    cells: (times || []).map((time) => {
      let best = 0;
      let courseLabel = '';
      for (const course of courses || []) {
        let n = 0;
        for (const p of participants || []) {
          if (p.seat === 'cancelled') continue;
          const dv = p.votes?.[date.id] ?? 0;
          const tv = p.votes?.[time.id] ?? 0;
          const cv = p.votes?.[course.id] ?? 0;
          if (dv >= 1 && tv >= 1 && cv >= 1) n += 1;
        }
        if (n > best) {
          best = n;
          courseLabel = course.label;
        }
      }
      return { timeId: time.id, timeLabel: time.label, available: best, courseLabel };
    }),
  }));
}

/**
 * 확정 때 가능한 사람을 도착 순으로 정원까지 참가, 나머지는 대기.
 * maxHeadcount 가 null 이면 전원 참가.
 */
export function assignSeats(eligible, maxHeadcount) {
  return rebalanceSeats({ going: eligible || [], waitlist: [], maxHeadcount });
}

/** 정원을 바꾸면 참가·대기를 도착 순으로 다시 나눈다. 취소한 사람은 넘기지 않는다. */
export function rebalanceSeats({ going, waitlist, maxHeadcount }) {
  const all = [...(going || []), ...(waitlist || [])].sort(byArrival);
  if (maxHeadcount == null) return { going: all, waitlist: [] };
  const cap = Math.max(0, maxHeadcount | 0);
  return { going: all.slice(0, cap), waitlist: all.slice(cap) };
}

/**
 * 참가자가 빠졌을 때 빈 자리만큼 대기 앞사람을 올린다.
 * 이미 참가 중인 사람의 자리는 빼지 않는다. 정원이 없으면 승급하지 않는다.
 */
export function promoteWaitlist({ goingCount, maxHeadcount, waitlist }) {
  const sorted = [...(waitlist || [])].sort(byArrival);
  if (maxHeadcount == null) return [];
  const open = (maxHeadcount | 0) - (goingCount | 0);
  if (open <= 0) return [];
  return sorted.slice(0, open);
}

export function seatsLeft(maxHeadcount, goingCount) {
  if (maxHeadcount == null) return null;
  return Math.max(0, (maxHeadcount | 0) - (goingCount | 0));
}

/** 총액을 참가 인원으로 나눈다. 1인 금액은 내린 값이고, 나머지는 원 단위로 남긴다. */
export function splitCost(items, headcount) {
  const lines = (items || []).map((it) => ({ label: String(it.label), amount: it.amount | 0 }));
  const total = lines.reduce((sum, it) => sum + it.amount, 0);
  const n = headcount | 0;
  if (n < 1) return { total, headcount: 0, perPerson: null, remainder: total, lines };
  const perPerson = Math.floor(total / n);
  const remainder = total - perPerson * n;
  return { total, headcount: n, perPerson, remainder, lines };
}

export function paceSecPerKm(distanceKm, durationSec) {
  if (!distanceKm || distanceKm <= 0 || !durationSec || durationSec <= 0) return null;
  return durationSec / distanceKm;
}

export function formatPace(secPerKm) {
  if (secPerKm == null || !Number.isFinite(secPerKm)) return '';
  const s = Math.round(secPerKm);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}'${String(r).padStart(2, '0')}"`;
}

export function leaderboard(records) {
  return (records || []).map((r) => {
    const paceSec = paceSecPerKm(r.distanceKm, r.durationSec);
    return { ...r, paceSec, pace: formatPace(paceSec) };
  }).sort((a, b) =>
    (a.paceSec ?? Infinity) - (b.paceSec ?? Infinity) ||
    b.distanceKm - a.distanceKm ||
    String(a.nickname).localeCompare(String(b.nickname), 'ko'));
}

export function replyRoster(expectedNames, participants) {
  const active = (participants || []).filter((p) => p.seat !== 'cancelled');
  const byKey = new Map(active.map((p) => [nicknameKey(p.nickname), p]));
  const used = new Set();
  const expected = (expectedNames || []).map((name) => {
    const p = byKey.get(nicknameKey(name));
    if (p) used.add(p.id);
    let status = 'missing';
    if (p && p.responded) status = 'replied';
    else if (p) status = 'joined';
    return { name, status, nickname: p ? p.nickname : null };
  });
  const others = active.filter((p) => !used.has(p.id)).map((p) => ({
    nickname: p.nickname,
    status: p.responded ? 'replied' : 'joined',
    seat: p.seat,
  }));
  return { expected, others };
}

export function mapLinks(place) {
  const q = encodeURIComponent(String(place || '').trim());
  return {
    naver: `https://map.naver.com/p/search/${q}`,
    kakao: `https://map.kakao.com/link/search/${q}`,
    google: `https://www.google.com/maps/search/?api=1&query=${q}`,
  };
}

export function formatDateKo(iso) {
  const [y, m, d] = String(iso).split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  const wd = ['일', '월', '화', '수', '목', '금', '토'][dt.getUTCDay()];
  return `${m}월 ${d}일 (${wd})`;
}

export function formatTimeKo(hhmm) {
  const [h, min] = String(hhmm).split(':').map(Number);
  const ap = h < 12 ? '오전' : '오후';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return min ? `${ap} ${h12}시 ${min}분` : `${ap} ${h12}시`;
}

/** 시계 시각에 시간을 더한다. 한국은 서머타임이 없어 달력 시각 그대로 더한다. */
export function addHours(date, time, hours) {
  const [y, m, d] = date.split('-').map(Number);
  const [hh, mm] = time.split(':').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d, hh + hours, mm));
  const p = (n) => String(n).padStart(2, '0');
  return {
    date: `${dt.getUTCFullYear()}-${p(dt.getUTCMonth() + 1)}-${p(dt.getUTCDate())}`,
    time: `${p(dt.getUTCHours())}:${p(dt.getUTCMinutes())}`,
  };
}

function compactStamp(date, time) {
  return `${date.replaceAll('-', '')}T${time.replaceAll(':', '')}00`;
}

export function googleCalendarUrl({ title, date, time, location, details }) {
  const end = addHours(date, time, 2);
  const u = new URL('https://calendar.google.com/calendar/render');
  u.searchParams.set('action', 'TEMPLATE');
  u.searchParams.set('text', title);
  u.searchParams.set('dates', `${compactStamp(date, time)}/${compactStamp(end.date, end.time)}`);
  u.searchParams.set('ctz', 'Asia/Seoul');
  if (location) u.searchParams.set('location', location);
  if (details) u.searchParams.set('details', details);
  return u.toString();
}

function icsEscape(s) {
  return String(s || '').replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/,/g, '\\,').replace(/;/g, '\\;');
}

export function buildIcs({ id, title, date, time, location, details, stamp }) {
  const end = addHours(date, time, 2);
  const dtstamp = stamp || '20260101T000000Z';
  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Runwoori//Crew//KO',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${id}@runwoori.com`,
    `DTSTAMP:${dtstamp}`,
    `DTSTART;TZID=Asia/Seoul:${compactStamp(date, time)}`,
    `DTEND;TZID=Asia/Seoul:${compactStamp(end.date, end.time)}`,
    `SUMMARY:${icsEscape(title)}`,
    location ? `LOCATION:${icsEscape(location)}` : '',
    `DESCRIPTION:${icsEscape(details || '')}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ].filter(Boolean);
  return `${lines.join('\r\n')}\r\n`;
}

/**
 * 고정 창 카운터. 창이 지나면 1부터 다시 세고, 한도에 닿으면 횟수를 올리지 않는다.
 */
export function rateLimitDecision({ count, windowStart, now, limit, windowMs }) {
  if (windowStart == null || now - windowStart >= windowMs) {
    return { allowed: true, count: 1, windowStart: now };
  }
  if (count >= limit) {
    const retryAfterMs = windowStart + windowMs - now;
    return {
      allowed: false,
      count,
      windowStart,
      retryAfterSec: Math.max(1, Math.ceil(retryAfterMs / 1000)),
    };
  }
  return { allowed: true, count: count + 1, windowStart };
}

export function seoulToday(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(now);
}

export function addDaysISO(iso, days) {
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  const p = (n) => String(n).padStart(2, '0');
  return `${dt.getUTCFullYear()}-${p(dt.getUTCMonth() + 1)}-${p(dt.getUTCDate())}`;
}
