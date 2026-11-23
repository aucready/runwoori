/* 크루 러닝 약속 공통. app.js 의 esc, toast, layout 을 쓴다. */
const CREW_PREP = '준비 중이에요. 크루 러닝 약속을 받는 서버가 아직 연결되지 않았어요. 잠시 뒤 다시 열어 주세요.';

function crewApiBase() {
  const set = (typeof CREW_API_BASE === 'string' ? CREW_API_BASE : '').trim().replace(/\/$/, '');
  if (set) return set;
  const host = location.hostname;
  if (host === 'localhost' || host === '127.0.0.1') return 'http://127.0.0.1:8787';
  return '';
}

class CrewPrep extends Error {
  constructor() { super(CREW_PREP); this.prep = true; }
}
class CrewError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

async function crewApi(path, opt = {}) {
  const base = crewApiBase();
  if (!base) throw new CrewPrep();
  const headers = { accept: 'application/json', ...(opt.headers || {}) };
  if (opt.body != null) headers['content-type'] = 'application/json';
  let res;
  try {
    res = await fetch(base + path, {
      method: opt.method || 'GET',
      headers,
      body: opt.body != null ? JSON.stringify(opt.body) : undefined,
      signal: AbortSignal.timeout(8000),
    });
  } catch {
    throw new CrewPrep();
  }
  const text = await res.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = null; }
  if (!res.ok) {
    if (!data || res.status === 502 || res.status === 503 || res.status === 504) throw new CrewPrep();
    throw new CrewError(data.error || '요청을 처리하지 못했어요.', res.status);
  }
  return data || {};
}

function crewBag(key) {
  try { return JSON.parse(localStorage.getItem(key) || '{}'); } catch { return {}; }
}
function crewHostKeyOf(val) {
  if (typeof val === 'string') return val;
  if (val && typeof val === 'object') return String(val.key || val.hostKey || val.k || '');
  return '';
}
function crewMeOf(val) {
  if (val && typeof val === 'object') return { token: val.token || '', nickname: val.nickname || '' };
  if (typeof val === 'string') return { token: val, nickname: '' };
  return null;
}
function crewMe(id) { return crewMeOf(crewBag('rw_crew_me_v1')[id]); }
function crewSaveMe(id, token, nickname) {
  const all = crewBag('rw_crew_me_v1');
  all[id] = { token, nickname };
  localStorage.setItem('rw_crew_me_v1', JSON.stringify(all));
}
function crewHostKey(id) { return crewHostKeyOf(crewBag('rw_crew_host_v1')[id]); }
function crewSaveHost(id, key) {
  const all = crewBag('rw_crew_host_v1');
  all[id] = key;
  localStorage.setItem('rw_crew_host_v1', JSON.stringify(all));
}
/** 이 기기 localStorage에 이미 있는 약속. 기존 rw_crew_host_v1 / rw_crew_me_v1 형식을 그대로 읽기만 하고 고치지 않아요. */
function crewKnownRuns() {
  const map = new Map();
  Object.entries(crewBag('rw_crew_me_v1')).forEach(([id, val]) => {
    if (!id || id === '__proto__' || id === 'constructor') return;
    const me = crewMeOf(val) || { token: '', nickname: '' };
    map.set(id, { id, key: '', token: me.token, nickname: me.nickname, hosted: false, joined: true });
  });
  Object.entries(crewBag('rw_crew_host_v1')).forEach(([id, val]) => {
    if (!id || id === '__proto__' || id === 'constructor') return;
    const key = crewHostKeyOf(val);
    const prev = map.get(id) || { id, token: '', nickname: '', joined: false };
    prev.key = key;
    prev.hosted = true;
    map.set(id, prev);
  });
  return [...map.values()];
}
async function crewRenderMine(mount) {
  if (!mount) return;
  const rows = crewKnownRuns();
  if (!rows.length) {
    mount.hidden = true;
    mount.innerHTML = '';
    return;
  }
  mount.hidden = false;
  const items = rows.map((row) => {
    const manage = row.hosted
      ? `<a class="ed-btn sm" href="${esc(row.key ? crewHostUrl(row.id, row.key) : `${location.origin}/crew/h.html?id=${encodeURIComponent(row.id)}`)}">관리하기</a>`
      : '';
    const join = `<a class="ed-btn ghost sm" href="${esc(crewRunUrl(row.id))}">참가 화면</a>`;
    return `<article class="cr-mine-item" data-run="${esc(row.id)}"><h3 class="cr-mine-title">저장된 약속</h3><p class="cr-mine-meta">${row.hosted ? '만든 약속' : '참여한 약속'}</p><div class="cr-actions">${manage}${join}</div></article>`;
  }).join('');
  mount.innerHTML = `<div class="ed-section-head"><span class="no">내 약속</span><h2 class="ed-h2">이 기기에 있는 약속</h2></div><div class="cr-mine-list">${items}</div>`;
  await Promise.all(rows.map(async (row) => {
    const el = mount.querySelector(`[data-run="${CSS.escape(row.id)}"]`);
    if (!el) return;
    try {
      const run = await crewApi('/v1/runs/' + encodeURIComponent(row.id));
      if (run && run.title) el.querySelector('.cr-mine-title').textContent = run.title;
      const bits = [row.hosted ? '만든 약속' : '참여한 약속'];
      if (run && run.statusLabel) bits.push(run.statusLabel);
      el.querySelector('.cr-mine-meta').textContent = bits.join(' · ');
    } catch {
      /* 제목을 못 받아도 목록과 관리하기 링크는 그대로 둡니다. */
    }
  }));
}

function crewShareUrl(id) {
  const base = crewApiBase();
  if (base) return `${base}/share/${id}`;
  return crewRunUrl(id);
}
function crewRunUrl(id) { return `${location.origin}/crew/r.html?id=${encodeURIComponent(id)}`; }
function crewHostUrl(id, key) { return `${location.origin}/crew/h.html?id=${encodeURIComponent(id)}#k=${encodeURIComponent(key)}`; }

function crewWon(n) {
  return `${Number(n || 0).toLocaleString('ko-KR')}원`;
}
function crewDur(sec) {
  sec = Math.round(sec || 0);
  const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60;
  return h ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`;
}
function crewPacePreview(km, sec) {
  if (!km || !sec) return '';
  const s = Math.round(sec / km);
  return `${Math.floor(s / 60)}'${String(s % 60).padStart(2, '0')}"/km`;
}
async function crewCopy(text) {
  try {
    await navigator.clipboard.writeText(text);
    if (typeof toast === 'function') toast('복사했어요');
  } catch {
    if (typeof toast === 'function') toast('길게 눌러 복사해 주세요');
  }
}
function crewPrepHtml() {
  return `<div class="ed-sample" role="status"><span class="ed-label">준비 중</span><span>${esc(CREW_PREP)}</span></div>`;
}
function crewEmpty(msg) {
  return `<div class="ed-empty">${esc(msg)}</div>`;
}

function crewMapsHtml(maps) {
  if (!maps) return '';
  return `<nav class="cr-maps" aria-label="집결지 지도"><a class="ed-link" href="${esc(maps.naver)}" target="_blank" rel="noopener">네이버 지도</a><a class="ed-link" href="${esc(maps.kakao)}" target="_blank" rel="noopener">카카오맵</a><a class="ed-link" href="${esc(maps.google)}" target="_blank" rel="noopener">구글 지도</a></nav>`;
}
function crewCalHtml(cal) {
  if (!cal) return '';
  return `<div class="cr-cal"><a class="ed-btn ghost sm" href="${esc(cal.ics)}">캘린더에 저장 (.ics)</a><a class="ed-btn ghost sm" href="${esc(cal.google)}" target="_blank" rel="noopener">Google 캘린더</a></div>`;
}
function crewPlanHtml(run) {
  const c = run.confirmed;
  if (!c) return '';
  let seat = '';
  if (run.status !== 'recruiting' && run.openJoin && run.maxHeadcount != null) {
    const left = run.seatsLeft == null ? 0 : run.seatsLeft;
    seat = `<p class="cr-seats"><b>${left}</b><span>자리 남음${left === 0 ? ' · 대기할 수 있어요' : ''}</span></p>`;
  } else if (run.status !== 'recruiting' && run.openJoin) {
    seat = `<p class="ed-small" style="margin-top:12px">인원 제한 없이 함께 달릴 수 있어요.</p>`;
  }
  const who = run.goingNames && run.goingNames.length ? `<p class="ed-small" style="margin-top:10px">같이 뛰는 사람 · ${esc(run.goingNames.join(', '))}</p>` : '';
  return `<section class="cr-plan"><div class="ed-label accent">${esc(run.statusLabel)}</div><h2 class="ed-h1" style="margin-top:8px">${esc(c.dateText)}</h2><p class="cr-plan-time">${esc(c.timeText)} 출발</p><h3 class="ed-h3">${esc(c.course)}</h3><p>${esc(c.place)}</p>${crewMapsHtml(c.maps)}${seat}${who}${crewCalHtml(c.calendar)}</section>`;
}
function crewCostHtml(expenses) {
  const s = expenses && expenses.split;
  if (!s || !s.lines || !s.lines.length) return '';
  const rows = s.lines.map((l) => `<div class="cr-cost-line"><span>${esc(l.label)}</span><b>${crewWon(l.amount)}</b></div>`).join('');
  const per = s.perPerson == null ? '참가자가 생기면 1인 금액을 계산해요.' : `1인 ${crewWon(s.perPerson)}`;
  const rem = s.remainder ? ` 나머지 ${crewWon(s.remainder)}은 인원으로 나누어 떨어지지 않아요. 1인 금액은 내린 값이에요.` : '';
  return `<section class="cr-block"><div class="ed-section-head"><span class="no">정산</span><h2 class="ed-h2">같이 나눌 돈</h2></div>${rows}<p class="cr-per">${per}</p><p class="ed-small">참가 ${s.headcount}명 · 합계 ${crewWon(s.total)}.${esc(rem)}</p></section>`;
}
function crewRecordsHtml(records) {
  if (!records || !records.length) return `<div class="ed-empty">아직 기록이 없어요. 달리고 나서 거리와 시간을 적어 주세요.</div>`;
  return `<ol class="cr-board">${records.map((r, i) => `<li><span class="ix">${String(i + 1).padStart(2, '0')}</span><div><b>${esc(r.nickname)}</b><span class="meta">${r.distanceKm}km · ${esc(crewDur(r.durationSec))} · ${esc(r.pace)}/km</span>${r.memo ? `<span class="memo">${esc(r.memo)}</span>` : ''}</div></li>`).join('')}</ol>`;
}
function crewByKind(options, kind) {
  return (options || []).filter((o) => o.kind === kind);
}
