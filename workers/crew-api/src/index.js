/**
 * Run우리 크루 러닝 약속 API.
 * 계정은 없다. 약속 주소(id)와 참가 토큰, 호스트 열쇠는 추측하기 어렵게 만들고
 * 서버에는 SHA-256 해시만 둔다. 호스트 열쇠 원문은 생성 응답에 한 번만 나간다.
 */
import {
  aggregateAvailability,
  assignSeats,
  buildIcs,
  dateTimeHeatmap,
  formatDateKo,
  formatTimeKo,
  googleCalendarUrl,
  leaderboard,
  mapLinks,
  nicknameKey,
  normalizeNickname,
  promoteWaitlist,
  rankCombos,
  rateLimitDecision,
  rebalanceSeats,
  replyRoster,
  seatsLeft,
  seoulToday,
  splitCost,
} from './logic.js';
import {
  LIMITS,
  parseHeadcount,
  validNickname,
  validateConfirm,
  validateCreate,
  validateExpenses,
  validatePatch,
  validateRecord,
  validateVotes,
} from './validate.js';

const TOKEN = /^[A-Za-z0-9_-]{20,80}$/;
const CREATE_LIMIT = 5;
const CREATE_WINDOW_MS = 60 * 60 * 1000;
const WRITE_LIMIT = 30;
const WRITE_WINDOW_MS = 10 * 60 * 1000;

class HttpError extends Error {
  constructor(status, message, headers = {}) {
    super(message);
    this.status = status;
    this.headers = headers;
  }
}

function allowedOrigin(origin) {
  if (!origin) return null;
  if (origin === 'https://runwoori.com') return origin;
  if (/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) return origin;
  return null;
}

function corsHeaders(origin) {
  const allowed = allowedOrigin(origin);
  const base = { vary: 'Origin' };
  if (!allowed) return base;
  return {
    ...base,
    'access-control-allow-origin': allowed,
    'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers': 'content-type,x-host-key,x-participant-token',
    'access-control-max-age': '86400',
  };
}

function json(data, status, origin, extra = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      ...corsHeaders(origin),
      ...extra,
    },
  });
}

function randomToken(bytes) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  let s = '';
  for (const b of a) s += String.fromCharCode(b);
  return btoa(s).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/g, '');
}

async function sha256Hex(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function safeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

async function readJson(request) {
  const len = Number(request.headers.get('content-length') || 0);
  if (len > 32_000) throw new HttpError(413, '내용이 너무 길어요.');
  const text = await request.text();
  if (text.length > 32_000) throw new HttpError(413, '내용이 너무 길어요.');
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    throw new HttpError(400, '요청 형식을 읽을 수 없어요.');
  }
}

function clientIp(request) {
  return request.headers.get('cf-connecting-ip')
    || (request.headers.get('x-forwarded-for') || '').split(',')[0].trim()
    || 'local';
}

async function takeLimit(env, request, action, limit, windowMs) {
  const ipHash = (await sha256Hex(`${action}:${clientIp(request)}`)).slice(0, 32);
  const bucket = `${action}:${ipHash}`;
  const now = Date.now();
  const row = await env.DB.prepare('SELECT window_start, count FROM rate_limits WHERE bucket = ?').bind(bucket).first();
  const decision = rateLimitDecision({
    count: row ? row.count : 0,
    windowStart: row ? row.window_start : null,
    now,
    limit,
    windowMs,
  });
  if (row) {
    await env.DB.prepare('UPDATE rate_limits SET window_start = ?, count = ? WHERE bucket = ?')
      .bind(decision.windowStart, decision.count, bucket).run();
  } else {
    await env.DB.prepare('INSERT INTO rate_limits (bucket, window_start, count) VALUES (?, ?, ?)')
      .bind(bucket, decision.windowStart, decision.count).run();
  }
  if (!decision.allowed) {
    throw new HttpError(429, '잠시 뒤에 다시 만들어 주세요. 짧은 시간에 요청이 너무 많아요.', {
      'retry-after': String(decision.retryAfterSec),
    });
  }
}

function rowsOf(result) {
  return result?.results || [];
}

async function getRun(db, id) {
  if (!TOKEN.test(id || '')) return null;
  return db.prepare('SELECT * FROM runs WHERE id = ?').bind(id).first();
}

async function getOptions(db, runId) {
  const res = await db.prepare(
    `SELECT id, run_id, kind, label, detail, sort_order FROM options
     WHERE run_id = ?
     ORDER BY CASE kind WHEN 'date' THEN 0 WHEN 'time' THEN 1 ELSE 2 END, sort_order, label`,
  ).bind(runId).all();
  return rowsOf(res);
}

function personFromRow(row, votes = {}) {
  return {
    id: row.id,
    nickname: row.nickname,
    nicknameKey: row.nickname_key,
    seat: row.seat,
    responded: row.responded ? 1 : 0,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    votes,
  };
}

async function getPeople(db, runId) {
  const parts = rowsOf(await db.prepare(
    'SELECT * FROM participants WHERE run_id = ? ORDER BY created_at, id',
  ).bind(runId).all());
  const voteRows = rowsOf(await db.prepare(
    `SELECT v.participant_id, v.option_id, v.state
     FROM votes v JOIN participants p ON p.id = v.participant_id
     WHERE p.run_id = ?`,
  ).bind(runId).all());
  const map = new Map(parts.map((p) => [p.id, personFromRow(p, {})]));
  for (const v of voteRows) {
    const p = map.get(v.participant_id);
    if (p) p.votes[v.option_id] = v.state;
  }
  return [...map.values()];
}

async function getExpenses(db, runId) {
  const res = await db.prepare(
    'SELECT id, label, amount, sort_order FROM expenses WHERE run_id = ? ORDER BY sort_order, id',
  ).bind(runId).all();
  return rowsOf(res).map((r) => ({ id: r.id, label: r.label, amount: r.amount }));
}

async function getRecords(db, runId) {
  const res = await db.prepare(
    `SELECT r.distance_km AS distanceKm, r.duration_sec AS durationSec, r.memo, p.nickname, p.id AS participantId
     FROM records r JOIN participants p ON p.id = r.participant_id
     WHERE p.run_id = ? AND p.seat = 'going'`,
  ).bind(runId).all();
  return leaderboard(rowsOf(res));
}

function optionView(opt, agg, withNames) {
  const row = agg.find((a) => a.id === opt.id);
  const view = {
    id: opt.id,
    kind: opt.kind,
    label: opt.label,
    detail: opt.detail || '',
    text: opt.kind === 'date' ? formatDateKo(opt.label) : opt.kind === 'time' ? formatTimeKo(opt.label) : opt.label,
    available: row ? row.available : 0,
    prefer: row ? row.prefer : 0,
  };
  if (opt.kind === 'course' && opt.detail) view.maps = mapLinks(opt.detail);
  if (withNames && row) view.names = row.names;
  return view;
}

function confirmedBlock(run, options, request, env) {
  if (run.status === 'recruiting') return null;
  const date = options.find((o) => o.id === run.confirmed_date_id);
  const time = options.find((o) => o.id === run.confirmed_time_id);
  const course = options.find((o) => o.id === run.confirmed_course_id);
  if (!date || !time || !course) return null;
  const page = `${env.SITE_ORIGIN || 'https://runwoori.com'}/crew/r.html?id=${run.id}`;
  return {
    dateId: date.id,
    timeId: time.id,
    courseId: course.id,
    date: date.label,
    time: time.label,
    course: course.label,
    place: course.detail,
    dateText: formatDateKo(date.label),
    timeText: formatTimeKo(time.label),
    maps: mapLinks(course.detail),
    calendar: {
      google: googleCalendarUrl({
        title: run.title,
        date: date.label,
        time: time.label,
        location: course.detail,
        details: `${run.memo ? `${run.memo}\n` : ''}${page}`,
      }),
      ics: new URL(request.url).origin + `/v1/runs/${run.id}/event.ics`,
    },
  };
}

function countSeats(people) {
  const counts = { voting: 0, going: 0, waitlist: 0, out: 0, cancelled: 0, replied: 0 };
  for (const p of people) {
    counts[p.seat] = (counts[p.seat] || 0) + 1;
    if (p.seat !== 'cancelled' && p.responded) counts.replied += 1;
  }
  return counts;
}

function waitlistPosition(people, id) {
  const list = people.filter((p) => p.seat === 'waitlist').sort((a, b) => a.createdAt.localeCompare(b.createdAt) || a.id.localeCompare(b.id));
  const i = list.findIndex((p) => p.id === id);
  return i < 0 ? null : i + 1;
}

function publicPayload(run, options, people, expenses, records, request, env) {
  const agg = aggregateAvailability(options, people);
  const counts = countSeats(people);
  const going = counts.going;
  const names = (() => {
    try {
      const v = JSON.parse(run.expected_names || '[]');
      return Array.isArray(v) ? v : [];
    } catch {
      return [];
    }
  })();
  return {
    id: run.id,
    title: run.title,
    memo: run.memo,
    hostNickname: run.host_nickname,
    status: run.status,
    statusLabel: { recruiting: '모집중', confirmed: '날짜확정', done: '완료' }[run.status],
    openJoin: Boolean(run.open_join),
    maxHeadcount: run.max_headcount,
    seatsLeft: run.status === 'recruiting' ? null : seatsLeft(run.max_headcount, going),
    counts,
    goingNames: people.filter((p) => p.seat === 'going').map((p) => p.nickname),
    expectedCount: names.length,
    options: options.map((o) => optionView(o, agg, false)),
    confirmed: confirmedBlock(run, options, request, env),
    expenses: {
      items: expenses.map(({ label, amount }) => ({ label, amount })),
      split: splitCost(expenses, going),
    },
    records,
  };
}

async function loadBundle(db, run) {
  const [options, people, expenses, records] = await Promise.all([
    getOptions(db, run.id),
    getPeople(db, run.id),
    getExpenses(db, run.id),
    getRecords(db, run.id),
  ]);
  return { options, people, expenses, records };
}

async function requireHost(db, run, request) {
  const key = request.headers.get('x-host-key') || '';
  if (!TOKEN.test(key)) throw new HttpError(401, '관리 열쇠가 필요해요. 약속을 만들 때 저장한 링크로 들어와 주세요.');
  const hash = await sha256Hex(key);
  if (!safeEqual(hash, run.host_key_hash)) throw new HttpError(401, '관리 열쇠가 맞지 않아요.');
  return true;
}

async function participantByToken(db, runId, token) {
  if (!TOKEN.test(token || '')) return null;
  const hash = await sha256Hex(token);
  return db.prepare('SELECT * FROM participants WHERE run_id = ? AND token_hash = ?').bind(runId, hash).first();
}

function tokenFrom(request) {
  return request.headers.get('x-participant-token') || '';
}

function isConstraint(err) {
  const msg = String(err?.message || err || '');
  return /UNIQUE|constraint/i.test(msg);
}

async function seatForNewcomer(db, run) {
  if (run.max_headcount == null) return 'going';
  const row = await db.prepare(
    `SELECT COUNT(*) AS n FROM participants WHERE run_id = ? AND seat = 'going'`,
  ).bind(run.id).first();
  return (row?.n || 0) >= run.max_headcount ? 'waitlist' : 'going';
}

function meView(row, people) {
  return {
    id: row.id,
    nickname: row.nickname,
    seat: row.seat,
    responded: Boolean(row.responded),
    waitlistPosition: row.seat === 'waitlist' ? waitlistPosition(people, row.id) : null,
  };
}

async function createRun(env, request, origin) {
  await takeLimit(env, request, 'create', CREATE_LIMIT, CREATE_WINDOW_MS);
  const body = await readJson(request);
  const parsed = validateCreate(body, seoulToday());
  if (!parsed.ok) throw new HttpError(400, parsed.error);
  const v = parsed.value;
  const id = randomToken(18);
  const hostKey = randomToken(18);
  const hostHash = await sha256Hex(hostKey);
  const participantToken = randomToken(18);
  const participantHash = await sha256Hex(participantToken);
  const participantId = randomToken(9);
  const now = new Date().toISOString();
  const stmts = [
    env.DB.prepare(
      `INSERT INTO runs (id, host_key_hash, title, memo, host_nickname, status, max_headcount, open_join, expected_names, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, 'recruiting', ?, ?, ?, ?, ?)`,
    ).bind(
      id, hostHash, v.title, v.memo, v.hostNickname, v.maxHeadcount, v.openJoin ? 1 : 0,
      JSON.stringify(v.expectedNames), now, now,
    ),
  ];
  v.dates.forEach((label, i) => {
    stmts.push(env.DB.prepare(
      'INSERT INTO options (id, run_id, kind, label, detail, sort_order) VALUES (?, ?, ?, ?, ?, ?)',
    ).bind(randomToken(9), id, 'date', label, '', i));
  });
  v.times.forEach((label, i) => {
    stmts.push(env.DB.prepare(
      'INSERT INTO options (id, run_id, kind, label, detail, sort_order) VALUES (?, ?, ?, ?, ?, ?)',
    ).bind(randomToken(9), id, 'time', label, '', i));
  });
  v.courses.forEach((course, i) => {
    stmts.push(env.DB.prepare(
      'INSERT INTO options (id, run_id, kind, label, detail, sort_order) VALUES (?, ?, ?, ?, ?, ?)',
    ).bind(randomToken(9), id, 'course', course.name, course.place, i));
  });
  stmts.push(env.DB.prepare(
    `INSERT INTO participants (id, run_id, token_hash, nickname, nickname_key, seat, responded, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, 'voting', 0, ?, ?)`,
  ).bind(participantId, id, participantHash, v.hostNickname, nicknameKey(v.hostNickname), now, now));
  await env.DB.batch(stmts);
  return json({
    id,
    hostKey,
    participantToken,
    sharePath: `/share/${id}`,
  }, 201, origin);
}

async function joinRun(env, request, run) {
  if (run.status === 'done') throw new HttpError(409, '이미 끝난 러닝이에요.');
  await takeLimit(env, request, 'join', WRITE_LIMIT, WRITE_WINDOW_MS);
  const body = await readJson(request);
  const now = new Date().toISOString();
  if (body.token) {
    const row = await participantByToken(env.DB, run.id, body.token);
    if (!row) throw new HttpError(401, '이 브라우저의 참가 정보를 찾지 못했어요. 닉네임을 다시 적어 주세요.');
    let seat = row.seat;
    if (row.seat === 'cancelled' || (run.status === 'confirmed' && (row.seat === 'out' || row.seat === 'voting'))) {
      if (run.status === 'confirmed' && !run.open_join) {
        throw new HttpError(409, '지금은 빈자리를 받지 않아요.');
      }
      seat = run.status === 'recruiting' ? 'voting' : await seatForNewcomer(env.DB, run);
      try {
        await env.DB.prepare(
          'UPDATE participants SET seat = ?, updated_at = ? WHERE id = ?',
        ).bind(seat, now, row.id).run();
      } catch (err) {
        if (isConstraint(err)) throw new HttpError(409, '이미 있는 닉네임이에요. 다른 이름으로 들어와 주세요.');
        throw err;
      }
    }
    const people = await getPeople(env.DB, run.id);
    const fresh = people.find((p) => p.id === row.id);
    return json({
      token: body.token,
      participant: meView({ ...row, seat: fresh?.seat || seat, responded: fresh?.responded || row.responded, nickname: row.nickname }, people),
      votes: fresh?.votes || {},
    }, 200, request.headers.get('origin'));
  }
  if (!validNickname(body.nickname)) throw new HttpError(400, '닉네임은 1~16자의 한글, 영문, 숫자로 적어 주세요.');
  const nickname = normalizeNickname(body.nickname);
  const key = nicknameKey(nickname);
  const total = await env.DB.prepare('SELECT COUNT(*) AS n FROM participants WHERE run_id = ?').bind(run.id).first();
  if ((total?.n || 0) >= LIMITS.participants) throw new HttpError(409, '이 약속은 더 받을 수 없어요.');
  let seat = 'voting';
  if (run.status === 'confirmed') {
    if (!run.open_join) throw new HttpError(409, '지금은 빈자리를 받지 않아요.');
    seat = await seatForNewcomer(env.DB, run);
  }
  const id = randomToken(9);
  const token = randomToken(18);
  const hash = await sha256Hex(token);
  try {
    await env.DB.prepare(
      `INSERT INTO participants (id, run_id, token_hash, nickname, nickname_key, seat, responded, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)`,
    ).bind(id, run.id, hash, nickname, key, seat, now, now).run();
  } catch (err) {
    if (isConstraint(err)) throw new HttpError(409, '이미 있는 닉네임이에요. 다른 이름으로 들어와 주세요.');
    throw err;
  }
  const people = await getPeople(env.DB, run.id);
  return json({
    token,
    participant: meView({ id, nickname, seat, responded: 0 }, people),
    votes: {},
  }, 201, request.headers.get('origin'));
}

async function saveVotes(env, request, run) {
  if (run.status !== 'recruiting') throw new HttpError(409, '날짜가 정해진 뒤에는 선택을 바꿀 수 없어요.');
  await takeLimit(env, request, 'vote', WRITE_LIMIT, WRITE_WINDOW_MS);
  const row = await participantByToken(env.DB, run.id, tokenFrom(request));
  if (!row || row.seat === 'cancelled') throw new HttpError(401, '먼저 닉네임을 적어 주세요.');
  const options = await getOptions(env.DB, run.id);
  const body = await readJson(request);
  const parsed = validateVotes(body, options.map((o) => o.id));
  if (!parsed.ok) throw new HttpError(400, parsed.error);
  const now = new Date().toISOString();
  const stmts = [
    env.DB.prepare('DELETE FROM votes WHERE participant_id = ?').bind(row.id),
    env.DB.prepare('UPDATE participants SET responded = 1, updated_at = ? WHERE id = ?').bind(now, row.id),
  ];
  for (const [optionId, state] of Object.entries(parsed.value)) {
    stmts.push(env.DB.prepare(
      'INSERT INTO votes (participant_id, option_id, state) VALUES (?, ?, ?)',
    ).bind(row.id, optionId, state));
  }
  await env.DB.batch(stmts);
  return json({ ok: true }, 200, request.headers.get('origin'));
}

async function cancelSeat(env, request, run) {
  if (run.status === 'done') throw new HttpError(409, '끝난 러닝의 참가 상태는 바꾸지 않아요.');
  const row = await participantByToken(env.DB, run.id, tokenFrom(request));
  if (!row) throw new HttpError(401, '참가 정보를 찾지 못했어요.');
  if (row.seat === 'cancelled') return json({ ok: true, promoted: null }, 200, request.headers.get('origin'));
  const wasGoing = row.seat === 'going';
  const now = new Date().toISOString();
  await env.DB.prepare('UPDATE participants SET seat = ?, updated_at = ? WHERE id = ?').bind('cancelled', now, row.id).run();
  let promoted = null;
  if (wasGoing && run.max_headcount != null && run.status === 'confirmed') {
    const goingRow = await env.DB.prepare(
      `SELECT COUNT(*) AS n FROM participants WHERE run_id = ? AND seat = 'going'`,
    ).bind(run.id).first();
    const waiting = rowsOf(await env.DB.prepare(
      `SELECT id, nickname, created_at AS createdAt FROM participants
       WHERE run_id = ? AND seat = 'waitlist' ORDER BY created_at, id`,
    ).bind(run.id).all());
    const up = promoteWaitlist({
      goingCount: goingRow?.n || 0,
      maxHeadcount: run.max_headcount,
      waitlist: waiting,
    });
    if (up[0]) {
      await env.DB.prepare('UPDATE participants SET seat = ?, updated_at = ? WHERE id = ?')
        .bind('going', now, up[0].id).run();
      promoted = up[0].nickname;
    }
  }
  return json({ ok: true, promoted }, 200, request.headers.get('origin'));
}

async function saveRecord(env, request, run) {
  if (run.status === 'recruiting') throw new HttpError(409, '러닝이 정해진 뒤에 기록을 적을 수 있어요.');
  await takeLimit(env, request, 'record', WRITE_LIMIT, WRITE_WINDOW_MS);
  const row = await participantByToken(env.DB, run.id, tokenFrom(request));
  if (!row || row.seat !== 'going') throw new HttpError(403, '참가가 확정된 분만 기록을 적을 수 있어요.');
  const body = await readJson(request);
  const parsed = validateRecord(body);
  if (!parsed.ok) throw new HttpError(400, parsed.error);
  const now = new Date().toISOString();
  await env.DB.prepare(
    `INSERT INTO records (participant_id, distance_km, duration_sec, memo, updated_at)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(participant_id) DO UPDATE SET
       distance_km = excluded.distance_km,
       duration_sec = excluded.duration_sec,
       memo = excluded.memo,
       updated_at = excluded.updated_at`,
  ).bind(row.id, parsed.value.distanceKm, parsed.value.durationSec, parsed.value.memo, now).run();
  return json({ ok: true, pace: leaderboard([{ ...parsed.value, nickname: row.nickname }])[0].pace }, 200, request.headers.get('origin'));
}

async function patchRun(env, request, run) {
  await requireHost(env.DB, run, request);
  const body = await readJson(request);
  const parsed = validatePatch(body);
  if (!parsed.ok) throw new HttpError(400, parsed.error);
  const v = parsed.value;
  if (run.status === 'done' && (v.maxHeadcount !== undefined || v.openJoin !== undefined)) {
    throw new HttpError(409, '끝난 러닝의 정원은 바꾸지 않아요.');
  }
  const now = new Date().toISOString();
  const max = v.maxHeadcount !== undefined ? v.maxHeadcount : run.max_headcount;
  const openJoin = v.openJoin !== undefined ? (v.openJoin ? 1 : 0) : run.open_join;
  await env.DB.prepare(
    `UPDATE runs SET title = ?, memo = ?, max_headcount = ?, open_join = ?, expected_names = ?, updated_at = ? WHERE id = ?`,
  ).bind(
    v.title ?? run.title,
    v.memo ?? run.memo,
    max,
    openJoin,
    v.expectedNames ? JSON.stringify(v.expectedNames) : run.expected_names,
    now,
    run.id,
  ).run();
  if (run.status === 'confirmed' && v.maxHeadcount !== undefined && v.maxHeadcount !== run.max_headcount) {
    const people = await getPeople(env.DB, run.id);
    const next = rebalanceSeats({
      going: people.filter((p) => p.seat === 'going'),
      waitlist: people.filter((p) => p.seat === 'waitlist'),
      maxHeadcount: v.maxHeadcount,
    });
    const stmts = [];
    for (const p of next.going) {
      if (p.seat !== 'going') stmts.push(env.DB.prepare('UPDATE participants SET seat = ?, updated_at = ? WHERE id = ?').bind('going', now, p.id));
    }
    for (const p of next.waitlist) {
      if (p.seat !== 'waitlist') stmts.push(env.DB.prepare('UPDATE participants SET seat = ?, updated_at = ? WHERE id = ?').bind('waitlist', now, p.id));
    }
    if (stmts.length) await env.DB.batch(stmts);
  }
  return json({ ok: true }, 200, request.headers.get('origin'));
}

async function confirmRun(env, request, run) {
  await requireHost(env.DB, run, request);
  if (run.status !== 'recruiting') throw new HttpError(409, '이미 날짜가 정해졌어요.');
  const body = await readJson(request);
  const { options, people } = await loadBundle(env.DB, run);
  const parsed = validateConfirm(body, options);
  if (!parsed.ok) throw new HttpError(400, parsed.error);
  let max = run.max_headcount;
  if (body.maxHeadcount !== undefined) {
    const cap = parseHeadcount(body.maxHeadcount);
    if (!cap.ok) throw new HttpError(400, cap.error);
    max = cap.value;
  }
  const openJoin = body.openJoin != null ? (body.openJoin ? 1 : 0) : run.open_join;
  const { date, time, course } = parsed.value;
  const eligible = people.filter((p) => {
    if (p.seat === 'cancelled') return false;
    return (p.votes[date.id] ?? 0) >= 1 && (p.votes[time.id] ?? 0) >= 1 && (p.votes[course.id] ?? 0) >= 1;
  });
  const assigned = assignSeats(eligible, max);
  const goingIds = new Set(assigned.going.map((p) => p.id));
  const waitIds = new Set(assigned.waitlist.map((p) => p.id));
  const now = new Date().toISOString();
  const stmts = [
    env.DB.prepare(
      `UPDATE runs SET status = 'confirmed', confirmed_date_id = ?, confirmed_time_id = ?, confirmed_course_id = ?,
         max_headcount = ?, open_join = ?, updated_at = ? WHERE id = ? AND status = 'recruiting'`,
    ).bind(date.id, time.id, course.id, max, openJoin, now, run.id),
  ];
  for (const p of people) {
    if (p.seat === 'cancelled') continue;
    const seat = goingIds.has(p.id) ? 'going' : waitIds.has(p.id) ? 'waitlist' : 'out';
    stmts.push(env.DB.prepare('UPDATE participants SET seat = ?, updated_at = ? WHERE id = ?').bind(seat, now, p.id));
  }
  await env.DB.batch(stmts);
  return json({ ok: true }, 200, request.headers.get('origin'));
}

async function finishRun(env, request, run) {
  await requireHost(env.DB, run, request);
  if (run.status !== 'confirmed') throw new HttpError(409, '날짜를 정한 뒤에 완료로 바꿀 수 있어요.');
  await env.DB.prepare(`UPDATE runs SET status = 'done', updated_at = ? WHERE id = ?`)
    .bind(new Date().toISOString(), run.id).run();
  return json({ ok: true }, 200, request.headers.get('origin'));
}

async function saveExpenses(env, request, run) {
  await requireHost(env.DB, run, request);
  if (run.status === 'recruiting') throw new HttpError(409, '날짜를 정한 뒤에 정산을 적을 수 있어요.');
  const body = await readJson(request);
  const parsed = validateExpenses(body);
  if (!parsed.ok) throw new HttpError(400, parsed.error);
  const stmts = [env.DB.prepare('DELETE FROM expenses WHERE run_id = ?').bind(run.id)];
  parsed.value.forEach((item, i) => {
    stmts.push(env.DB.prepare(
      'INSERT INTO expenses (id, run_id, label, amount, sort_order) VALUES (?, ?, ?, ?, ?)',
    ).bind(randomToken(9), run.id, item.label, item.amount, i));
  });
  stmts.push(env.DB.prepare('UPDATE runs SET updated_at = ? WHERE id = ?').bind(new Date().toISOString(), run.id));
  await env.DB.batch(stmts);
  return json({ ok: true }, 200, request.headers.get('origin'));
}

async function deleteRun(env, request, run) {
  await requireHost(env.DB, run, request);
  const ids = rowsOf(await env.DB.prepare('SELECT id FROM participants WHERE run_id = ?').bind(run.id).all()).map((r) => r.id);
  const stmts = [];
  for (const pid of ids) {
    stmts.push(env.DB.prepare('DELETE FROM votes WHERE participant_id = ?').bind(pid));
    stmts.push(env.DB.prepare('DELETE FROM records WHERE participant_id = ?').bind(pid));
  }
  stmts.push(env.DB.prepare('DELETE FROM participants WHERE run_id = ?').bind(run.id));
  stmts.push(env.DB.prepare('DELETE FROM options WHERE run_id = ?').bind(run.id));
  stmts.push(env.DB.prepare('DELETE FROM expenses WHERE run_id = ?').bind(run.id));
  stmts.push(env.DB.prepare('DELETE FROM runs WHERE id = ?').bind(run.id));
  await env.DB.batch(stmts);
  return json({ ok: true }, 200, request.headers.get('origin'));
}

function escHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function shareHtml(run, options, env) {
  const origin = env.SITE_ORIGIN || 'https://runwoori.com';
  const dest = `${origin}/crew/r.html?id=${encodeURIComponent(run.id)}`;
  const dates = options.filter((o) => o.kind === 'date').map((o) => formatDateKo(o.label));
  let description = `${run.host_nickname}님이 크루 러닝 날짜를 받고 있어요. 가입 없이 가능한 날을 골라 주세요.`;
  if (dates.length) description = `${dates.slice(0, 3).join(', ')} 중에서 고르는 중이에요. ${description}`;
  if (run.status !== 'recruiting') {
    const date = options.find((o) => o.id === run.confirmed_date_id);
    const time = options.find((o) => o.id === run.confirmed_time_id);
    const course = options.find((o) => o.id === run.confirmed_course_id);
    if (date && time && course) {
      description = `${formatDateKo(date.label)} ${formatTimeKo(time.label)} · ${course.label}. ${run.title}`;
    }
  }
  const title = `${run.title} · 크루 러닝 약속`;
  const image = `${origin}/assets/icons/og-image.png`;
  return `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escHtml(title)}</title>
<meta name="robots" content="noindex">
<meta name="description" content="${escHtml(description)}">
<meta property="og:site_name" content="Run우리">
<meta property="og:type" content="website">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="${escHtml(title)}">
<meta property="og:description" content="${escHtml(description)}">
<meta property="og:image" content="${escHtml(image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta http-equiv="refresh" content="1;url=${escHtml(dest)}">
<link rel="canonical" href="${escHtml(dest)}">
<style>body{margin:0;background:#F6F2EA;color:#1C1B18;font-family:"Apple SD Gothic Neo","Noto Sans KR",sans-serif}main{max-width:32rem;margin:0 auto;padding:48px 24px}p{color:#47443D;line-height:1.7}a{color:#1C1B18}</style>
</head><body><main>
<p>Run우리 · 크루 러닝 약속</p>
<h1>${escHtml(run.title)}</h1>
<p>${escHtml(description)}</p>
<p><a href="${escHtml(dest)}">가능한 날 고르러 가기</a></p>
</main></body></html>`;
}

async function handle(request, env) {
  const origin = request.headers.get('origin');
  if (!env.DB) return json({ error: '준비 중이에요. 잠시 뒤 다시 열어 주세요.' }, 503, origin);
  if (origin && !allowedOrigin(origin) && request.method !== 'GET') {
    return json({ error: '이 주소에서는 약속을 열 수 없어요.' }, 403, origin);
  }
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: corsHeaders(origin) });

  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, '') || '/';
  const method = request.method;

  if (method === 'GET' && path === '/health') return json({ ok: true }, 200, origin);

  const share = path.match(/^\/share\/([^/]+)$/);
  if (method === 'GET' && share) {
    const run = await getRun(env.DB, share[1]);
    if (!run) return new Response('약속을 찾지 못했어요.', { status: 404, headers: { 'content-type': 'text/plain; charset=utf-8' } });
    const options = await getOptions(env.DB, run.id);
    const html = shareHtml(run, options, env).replace(
      '<meta property="og:image"',
      `<meta property="og:url" content="${escHtml(url.origin + path)}">\n<meta property="og:image"`,
    );
    return new Response(html, {
      status: 200,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'no-store',
        'x-content-type-options': 'nosniff',
        'referrer-policy': 'no-referrer',
      },
    });
  }

  const ics = path.match(/^\/v1\/runs\/([^/]+)\/event\.ics$/);
  if (method === 'GET' && ics) {
    const run = await getRun(env.DB, ics[1]);
    if (!run || run.status === 'recruiting') throw new HttpError(404, '아직 날짜가 정해지지 않았어요.');
    const options = await getOptions(env.DB, run.id);
    const date = options.find((o) => o.id === run.confirmed_date_id);
    const time = options.find((o) => o.id === run.confirmed_time_id);
    const course = options.find((o) => o.id === run.confirmed_course_id);
    if (!date || !time || !course) throw new HttpError(404, '일정을 찾지 못했어요.');
    const body = buildIcs({
      id: run.id,
      title: run.title,
      date: date.label,
      time: time.label,
      location: course.detail,
      details: run.memo || 'Run우리 크루 러닝',
      stamp: new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z'),
    });
    return new Response(body, {
      status: 200,
      headers: {
        'content-type': 'text/calendar; charset=utf-8',
        'content-disposition': 'attachment; filename="runwoori-crew.ics"',
        'cache-control': 'no-store',
      },
    });
  }

  if (method === 'POST' && path === '/v1/runs') return createRun(env, request, origin);

  const runPath = path.match(/^\/v1\/runs\/([^/]+)(?:\/([^/]+))?$/);
  if (!runPath) throw new HttpError(404, '주소를 찾지 못했어요.');
  const run = await getRun(env.DB, runPath[1]);
  if (!run) throw new HttpError(404, '약속을 찾지 못했어요. 링크를 다시 확인해 주세요.');
  const sub = runPath[2] || '';

  if (method === 'GET' && sub === '') {
    const bundle = await loadBundle(env.DB, run);
    return json(publicPayload(run, bundle.options, bundle.people, bundle.expenses, bundle.records, request, env), 200, origin);
  }
  if (method === 'GET' && sub === 'me') {
    const row = await participantByToken(env.DB, run.id, tokenFrom(request));
    if (!row) throw new HttpError(401, '이 브라우저의 참가 정보를 찾지 못했어요.');
    const people = await getPeople(env.DB, run.id);
    const me = people.find((p) => p.id === row.id);
    const record = (await getRecords(env.DB, run.id)).find((r) => r.participantId === row.id) || null;
    return json({ participant: meView(row, people), votes: me?.votes || {}, record }, 200, origin);
  }
  if (method === 'GET' && sub === 'host') {
    await requireHost(env.DB, run, request);
    const bundle = await loadBundle(env.DB, run);
    const dates = bundle.options.filter((o) => o.kind === 'date');
    const times = bundle.options.filter((o) => o.kind === 'time');
    const courses = bundle.options.filter((o) => o.kind === 'course');
    const agg = aggregateAvailability(bundle.options, bundle.people);
    let expected = [];
    try {
      const v = JSON.parse(run.expected_names || '[]');
      expected = Array.isArray(v) ? v : [];
    } catch { expected = []; }
    const payload = publicPayload(run, bundle.options, bundle.people, bundle.expenses, bundle.records, request, env);
    payload.options = bundle.options.map((o) => optionView(o, agg, true));
    payload.recommendation = rankCombos(dates, times, courses, bundle.people).slice(0, 8);
    payload.heatmap = dateTimeHeatmap(dates, times, courses, bundle.people);
    payload.roster = replyRoster(expected, bundle.people);
    payload.participants = bundle.people
      .filter((p) => p.seat !== 'cancelled')
      .map((p) => ({
        nickname: p.nickname,
        seat: p.seat,
        responded: Boolean(p.responded),
        createdAt: p.createdAt,
        votes: p.votes,
      }));
    payload.cancelled = bundle.people.filter((p) => p.seat === 'cancelled').map((p) => p.nickname);
    return json(payload, 200, origin);
  }
  if (method === 'POST' && sub === 'participants') return joinRun(env, request, run);
  if (method === 'PUT' && sub === 'votes') return saveVotes(env, request, run);
  if (method === 'POST' && sub === 'cancel') return cancelSeat(env, request, run);
  if (method === 'PUT' && sub === 'record') return saveRecord(env, request, run);
  if (method === 'PATCH' && sub === '') return patchRun(env, request, run);
  if (method === 'POST' && sub === 'confirm') return confirmRun(env, request, run);
  if (method === 'POST' && sub === 'done') return finishRun(env, request, run);
  if (method === 'PUT' && sub === 'expenses') return saveExpenses(env, request, run);
  if (method === 'DELETE' && sub === '') return deleteRun(env, request, run);
  throw new HttpError(404, '주소를 찾지 못했어요.');
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('origin');
    try {
      return await handle(request, env);
    } catch (err) {
      if (err instanceof HttpError) return json({ error: err.message }, err.status, origin, err.headers);
      console.error(err);
      return json({ error: '잠깐 문제가 생겼어요. 잠시 뒤 다시 열어 주세요.' }, 500, origin);
    }
  },
};
