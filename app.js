/* Run우리 공통 스크립트 — 에디토리얼 시안(ed- 컴포넌트) + 실제 data.js 연동 */
/* 사이트 이름은 여기 한 곳에서 관리 (정적 HTML의 <title>·메타·로고 이미지는 이름 변경 시 별도 교체: CHANGELOG 참고) */
const SITE = { name: 'Run우리', tagline: '마라톤·러닝 대회 일정' };
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const DAY = 86400000;
const WD = ['일','월','화','수','목','금','토'];
const EN = ['SUN','MON','TUE','WED','THU','FRI','SAT'];
function pd(s){ if(!s) return null; const [y,m,d]=s.split('-').map(Number); return new Date(y,m-1,d); }
function today(){ const t=new Date(); return new Date(t.getFullYear(),t.getMonth(),t.getDate()); }
function diff(a,b){ return Math.round((a-b)/DAY); }
const p2 = n => String(n).padStart(2,'0');
function iso(d){ return `${d.getFullYear()}-${p2(d.getMonth()+1)}-${p2(d.getDate())}`; }
function fmt(d){ return `${p2(d.getMonth()+1)}.${p2(d.getDate())}(${WD[d.getDay()]})`; }
function fmtFull(d){ return `${d.getFullYear()}.${p2(d.getMonth()+1)}.${p2(d.getDate())}(${WD[d.getDay()]})`; }
function fmtShort(d){ return `${d.getMonth()+1}.${d.getDate()}`; }
function ddayText(n){ return n===0?'D-DAY':(n>0?`D-${n}`:`D+${-n}`); }
function esc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
const BM = '<svg viewBox="0 0 18 22" aria-hidden="true"><path d="M3 2.5h12v17.2l-6-4.2-6 4.2z"/></svg>';
const SEARCH_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/></svg>';

/* 접수 상태: 접수중 / 마감임박(마감 10일 이내 — 러닝온 기준) / 접수예정 / 마감 / 접수 확인(정보 없음) */
const URGENT_DAYS = 10;
/* ── 데이터 로드: data/races.json (수집기 산출물) → window.RACES ── */
window.RACES = []; window.RACES_META = null;
function man(n){ if(n==null) return null; const m=n/10000; return (Number.isInteger(m)?m:+m.toFixed(2).replace(/0+$/,''))+'만원'; }
function feeRange(r){
  if(r.fee_min==null) return '';
  if(r.fee_min===0&&r.fee_max===0) return '무료';
  const f=n=>n>=10000&&n%1000===0?man(n):n.toLocaleString('ko-KR')+'원';
  return r.fee_min===r.fee_max?f(r.fee_min):f(r.fee_min)+' ~ '+f(r.fee_max);
}
function adapt(r){
  const t=today(), start=r.date, end=r.end_date||r.date;
  const ongoing = start<iso(t) && end>=iso(t);
  return { id:r.id, name:r.name, start, end, date: ongoing?end:start, ongoing,
    region:r.region||'', venue:r.venue||'', organizer:r.organizer||'', type:r.category||'',
    dist:r.distances.map(d=>d.label), distances:r.distances, distTags:r.dist_tags||[],
    fee:feeRange(r), fee_min:r.fee_min, fee_max:r.fee_max, open:r.reg_open, close:r.reg_close, regState:r.reg_state, regNote:r.reg_note,
    official:r.official_url, regUrl:r.reg_url, sources:r.sources||{}, startTime:r.start_time, real:true };
}
function loadRaces(){
  return fetch('data/races.json',{cache:'no-cache'}).then(x=>{ if(!x.ok) throw new Error('races.json '+x.status); return x.json(); })
   .then(j=>{ window.RACES_META={fetched_at:j.fetched_at,count:j.count,window:j.window,sources:j.sources,coverage:j.coverage}; window.RACES=j.races.map(adapt); })
   .catch(e=>{ console.warn('대회 데이터를 불러오지 못했어요',e); window.RACES_FAILED=true; });
}
const RACES_READY = loadRaces();

/* 접수 상태: 접수중 / 마감임박(마감 10일 이내 — 러닝온 기준) / 접수예정 / 마감 / 접수 확인(정보 없음) */
function status(r){
  const t=today(), race=pd(r.date), open=pd(r.open), close=pd(r.close);
  if(race<t) return {key:'ended', label:'종료'};
  if(r.regState==='full') return {key:'closed', label:'정원 마감'};
  if(r.regState==='suspended') return {key:'closed', label:'접수 중단'};
  if(close && close<t) return {key:'closed', label:'마감'};
  if(r.regState==='closed') return {key:'closed', label:'마감'};
  if(open && open>t) return {key:'soon', label:'접수예정', n:diff(open,t)};
  if(r.regState==='upcoming') return {key:'soon', label:'접수예정'};
  if(close && diff(close,t)<=URGENT_DAYS) return {key:'urgent', label:'마감임박', n:diff(close,t)};
  if(close || open || r.regState==='open' || r.regState==='ongoing') return {key:'open', label:'접수중'};
  return {key:'info', label:'접수 확인'};
}
function enrich(r){ const t=today(); return {...r, st:status(r), d:diff(pd(r.date),t), dt:pd(r.date)}; }
const allRaces = () => window.RACES.map(enrich);

/* 관심 대회 / 관심 코스 (localStorage) */
function store(key){ return { get(){ try{return JSON.parse(localStorage.getItem(key))||[]}catch(e){return []} },
  has(id){return this.get().includes(id)},
  toggle(id){ let a=this.get(); a=a.includes(id)?a.filter(x=>x!==id):[...a,id]; localStorage.setItem(key,JSON.stringify(a)); return a.includes(id);} }; }
const favs = store('rr_favs_v1'), cfavs = store('rr_cfavs_v1');

function feeText(r){ return r.fee||'참가비 확인 필요'; }
function regText(r){
  const t=today();
  if(r.ongoing) return `진행 중 · ~${fmtShort(pd(r.end))} 까지`;
  if(r.st.key==='soon' && r.open) return `접수 ${fmtShort(pd(r.open))} 시작 (D-${diff(pd(r.open),t)})`;
  if(r.st.key==='soon') return '접수 예정 · 일정 확인 필요';
  if(r.close && r.st.key!=='closed') return `접수 ~${fmtShort(pd(r.close))} (D-${diff(pd(r.close),t)})`;
  if(r.close) return `접수 마감 ${fmtShort(pd(r.close))}`;
  if(r.st.key==='closed') return '접수 마감';
  if(r.st.key==='info') return '접수 정보 확인 필요';
  return '마감일 확인 필요';
}
const sep='<span class="sep">·</span>';
function bookmark(id,on,attr='data-fav',label='관심 대회 저장'){ return `<button class="ed-bookmark ${on?'is-on':''}" aria-pressed="${!!on}" aria-label="${label}" ${attr}="${id}">${BM}</button>`; }
function ddayCls(r){ if(r.st.key==='closed'||r.st.key==='ended') return ''; return (r.st.key==='urgent'||(r.d>=0&&r.d<=7))?'soon':''; }
function raceRow(r){
  const fav=favs.has(r.id), dist=r.dist.length?(r.dist.slice(0,3).join(' · ')+(r.dist.length>3?` 외 ${r.dist.length-3}개`:'')):'종목 확인 필요';
  return `<article class="ed-race ${fav?'is-saved':''}" data-id="${r.id}">
    <div class="ed-race-date"><b>${p2(r.dt.getDate())}</b><span>${r.dt.getMonth()+1}월 ${WD[r.dt.getDay()]}</span></div>
    <div class="ed-race-body"><div class="ed-race-top"><span class="ed-status ${r.st.key}">${r.st.label}</span></div>
      <h3><a class="row-link" href="race/${r.id}.html">${esc(r.name)}</a></h3>
      <p class="ed-meta">${[esc(r.region||'지역 확인 필요'),r.type?esc(r.type):'',esc(dist)].filter(Boolean).join(sep)}</p>
      <p class="ed-meta">${regText(r)}${sep}${esc(feeText(r))}</p></div>
    <div class="ed-race-side"><div class="ed-dday ${ddayCls(r)}">${ddayText(r.d)}</div>${bookmark(r.id,fav)}</div>
  </article>`;
}

/* 북마크 / 토스트 / 내비 카운트 */
function updateNavCount(){ const n=favs.get().length; $$('[data-saved-count]').forEach(e=>{e.textContent=n; e.hidden=n===0;}); }
function toast(msg){ let t=$('#toast'); if(!t){t=document.createElement('div');t.id='toast';t.className='ed-toastwrap';t.setAttribute('role','status');document.body.appendChild(t);} t.innerHTML=`<span class="ed-toast">${esc(msg)}</span>`; t.classList.add('show'); clearTimeout(t._h); t._h=setTimeout(()=>t.classList.remove('show'),1800); }
function bindFav(onChange){
  document.addEventListener('click',e=>{
    const b=e.target.closest('[data-fav],[data-cfav]'); if(!b) return; e.preventDefault(); e.stopPropagation();
    const isC=b.hasAttribute('data-cfav'); const id=b.dataset.fav||b.dataset.cfav;
    const on=(isC?cfavs:favs).toggle(id);
    $$(`[${isC?'data-cfav':'data-fav'}="${id}"]`).forEach(x=>{ x.classList.toggle('is-on',on); x.setAttribute('aria-pressed',on); x.classList.remove('pop'); void x.offsetWidth; x.classList.add('pop'); });
    $$(`.ed-race[data-id="${id}"]`).forEach(c=>c.classList.toggle('is-saved',on));
    updateNavCount(); toast(on?(isC?'관심 코스에 저장했어요':'관심 대회에 저장했어요'):'저장을 해제했어요'); if(onChange) onChange();
  }, true);
}

/* 레이아웃: 마스트헤드(+데스크톱 메뉴), 하단 탭바, 푸터 */
function updatedText(){
  const M=window.RACES_META; if(!M||!M.fetched_at) return window.RACES_FAILED?'대회 데이터 불러오기 실패':'데이터 불러오는 중';
  const m=M.fetched_at.match(/(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d)/); if(!m) return '';
  const age=(Date.now()-new Date(M.fetched_at).getTime())/3600000;
  return `마지막 업데이트 ${m[2]}.${m[3]} ${m[4]}:${m[5]}${age>72?' · 오래된 데이터':''}`;
}
function fillUpdated(){ if(window.RACES_FAILED&&$('#main')&&!$('#loadfail')) $('#main').insertAdjacentHTML('afterbegin','<p class="ed-note" id="loadfail" role="alert" style="margin:16px var(--page-x) 0">대회 데이터를 불러오지 못했어요. 인터넷 연결을 확인하고 새로고침해 주세요. (이 폴더를 파일로 직접 열었다면 웹 서버로 열어야 해요.)</p>'); $$('[data-updated]').forEach(e=>{ e.textContent=updatedText(); }); const n=$('[data-count-all]'); if(n&&window.RACES_META) n.textContent=window.RACES_META.count; }
RACES_READY.then(fillUpdated);
function layout(active){
  document.body.classList.add('ed-root');
  const t=today();
  const nav=[['index.html','대회 달력','races'],['my.html','나의 레이스','home'],['blog.html','러닝 가이드','blog'],['courses.html','러닝 코스','courses'],['tools.html','훈련 · 페이스','tools'],['saved.html','저장','saved']];
  const bottom=[['index.html','대회','races'],['my.html','나의 레이스','home'],['blog.html','가이드','blog'],['saved.html','저장','saved']];
  const badge=n=>n==='saved'?'<span class="n" data-saved-count hidden>0</span>':'';
  const head=`<a class="skip-link" href="${location.pathname}${location.search}#main">본문으로 건너뛰기</a><header class="ed-mast"><div class="ed-wrap"><div class="ed-mast-top"><span class="ed-label">${t.getFullYear()}.${p2(t.getMonth()+1)}.${p2(t.getDate())} ${EN[t.getDay()]}</span><span class="ed-label" data-updated aria-live="polite">${updatedText()}</span></div>
    <div class="ed-mast-row"><a class="ed-wordmark" href="index.html" aria-label="${SITE.name} 홈"><img src="assets/logo/runwoori-wordmark-light-small.svg" alt="${SITE.name}" width="118" height="28"></a>
    <nav class="ed-mast-nav" aria-label="주 메뉴">${nav.map(n=>`<a href="${n[0]}" class="${n[2]===active?'is-on':''}" ${n[2]===active?'aria-current="page"':''}>${n[1]}${badge(n[2])}</a>`).join('')}</nav>
    <div class="ed-mast-links"><a class="ed-link ${active==='courses'?'is-on':''}" href="courses.html">코스</a><a class="ed-link ${active==='tools'?'is-on':''}" href="tools.html">훈련</a></div></div></div></header>`;
  const bn=`<nav class="ed-tabbar" aria-label="하단 메뉴">${bottom.map(n=>`<a href="${n[0]}" class="${n[2]===active?'is-on':''}" ${n[2]===active?'aria-current="page"':''}>${n[1]}${badge(n[2])}</a>`).join('')}</nav>`;
  const foot=`<footer class="ed-footer"><div class="ed-wrap"><div class="ed-rule" style="border-color:var(--ink)"></div><p class="ed-small" style="padding-top:14px"><img class="ed-foot-logo" src="assets/logo/runwoori-wordmark-light-small.svg" alt="${SITE.name}" width="101" height="24"><br>${SITE.name}는 개인 프로젝트입니다. 대회 일정은 <a href="https://runningon.co.kr" rel="noopener" target="_blank">러닝온</a>과 <a href="https://www.kormarathon.com" rel="noopener" target="_blank">KorMarathon</a>의 공개 페이지에서 하루 한 번 자동 수집해 정리합니다. 일정·참가비·접수 기간은 바뀔 수 있으니 신청 전 반드시 공식 홈페이지에서 확인하세요.<br><span data-updated>${updatedText()}</span></p>
    <nav class="ed-foot-links" aria-label="사이트 정보"><a href="about.html">사이트 소개</a><a href="privacy.html">개인정보처리방침</a><a href="terms.html">이용약관</a><a href="contact.html">문의하기</a></nav></div></footer>`;
  document.body.insertAdjacentHTML('afterbegin',head);
  document.body.insertAdjacentHTML('beforeend',foot+bn);
  updateNavCount();
}
/* 정규 주소(canonical)·og:url — 도메인 연결 후 tools/set_domain.sh 가 정적 태그를 넣어 두면, ?id= 같은 동적 페이지는 여기서 쿼리까지 맞춘다 */
function setCanonicalQuery(qs){
  const c=$('link[rel=canonical]'); if(!c) return;
  const u=new URL(c.href); u.search=qs?('?'+qs):''; c.href=u.href;
  const o=$('meta[property="og:url"]'); if(o) o.setAttribute('content',u.href);
}
const sampleNote = txt => `<div class="ed-sample"><span class="ed-label">안내</span><span>${txt||'대회 정보는 공개 페이지에서 자동 수집한 것이에요. 접수는 반드시 공식 홈페이지에서 확인하세요.'}</span></div>`;
const secHead=(no,title,more,major)=>`<div class="ed-section-head ${major?'major':''}"><span class="no">${no}</span><h2 class="ed-h2">${title}</h2>${more?`<a class="ed-link" href="${more[0]}">${more[1]} →</a>`:''}</div>`;

/* ── 페이스 계산기 (문장형 ed-calc) ── */
const fmtPace = s => { s=Math.round(s); return `${Math.floor(s/60)}'${p2(s%60)}"`; };
const fmtTime = s => { s=Math.round(s); const h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60; return `${h}:${p2(m)}:${p2(x)}`; };
const dname = k => ({5:'5K',10:'10K',21.0975:'하프',42.195:'풀코스'}[k]||(+(+k).toFixed(2))+'K');
function paceCalcHtml(opt={}){
  return `<div class="ed-calc" data-pace>
    ${opt.mode?`<div class="ed-seg" style="margin-bottom:16px"><button class="is-on" data-mode="time">기록 → 페이스</button><button data-mode="pace">페이스 → 기록</button></div>`:''}
    <div class="ed-label" style="margin-bottom:2px">거리</div>
    <div class="ed-calc-dist"><button data-km="5">5K</button><button data-km="10">10K</button><button class="is-on" data-km="21.0975">하프</button><button data-km="42.195">풀</button><button data-km="0">직접 입력</button></div>
    <input class="ed-input pc-km ed-pc-km" type="number" step="0.01" min="0" inputmode="decimal" placeholder="거리(km) 예: 7.5" aria-label="거리(km)" hidden>
    <p class="ed-calc-sentence pc-time">목표 기록 <span class="inp"><input class="pc-h" inputmode="numeric" value="1" aria-label="시간"></span><span class="colon">:</span><span class="inp"><input class="pc-m" inputmode="numeric" value="55" aria-label="분"></span><span class="colon">:</span><span class="inp"><input class="pc-s" inputmode="numeric" value="00" aria-label="초"></span></p>
    <p class="ed-calc-sentence pc-pace" hidden>1km당 <span class="inp"><input class="pc-pm" inputmode="numeric" value="5" aria-label="분"></span><span class="colon">'</span><span class="inp"><input class="pc-ps" inputmode="numeric" value="27" aria-label="초"></span><span class="colon">"</span></p>
    <div class="ed-calc-out"><div><div class="ed-label nocase pc-label" style="margin-bottom:8px">1km 평균 페이스</div><div class="v pc-main">-</div></div><div class="sub pc-sub"></div></div>
    ${opt.splits?`<table class="ed-table pc-splits" style="margin-top:22px"><thead><tr><th>구간</th><th>누적 시간</th></tr></thead><tbody></tbody></table>
    <table class="ed-table pc-pred" style="margin-top:22px"><thead><tr><th>다른 거리 예상 기록 (리겔 공식 · 단순 추정)</th><th>기록</th></tr></thead><tbody></tbody></table>`:''}
  </div>`;
}
function initPace(root){
  const st={km:21.0975,mode:'time'};
  const val=sel=>{const e=$(sel,root);return e?(parseFloat(e.value)||0):0;};
  const K=()=>st.km||val('.pc-km');
  function calc(){
    const out=$('.pc-main',root), sub=$('.pc-sub',root), lab=$('.pc-label',root), k=K();
    let pace,total;
    if(st.mode==='time'){ total=val('.pc-h')*3600+val('.pc-m')*60+val('.pc-s'); pace=total/k; } else { pace=val('.pc-pm')*60+val('.pc-ps'); total=pace*k; }
    const tb=$('.pc-splits tbody',root), pr=$('.pc-pred tbody',root);
    if(!pace||!isFinite(pace)||!k){ out.textContent='–'; sub.innerHTML='거리와 기록을 입력해 주세요'; if(tb) tb.innerHTML=''; if(pr) pr.innerHTML=''; return; }
    if(st.mode==='time'){ lab.textContent='1km 평균 페이스'; out.innerHTML=fmtPace(pace)+'<em>/km</em>'; } else { lab.textContent='예상 완주 기록'; out.innerHTML=fmtTime(total); }
    sub.innerHTML=`시속 ${(3600/pace).toFixed(1)} km<br>${st.mode==='time'?'완주 '+fmtTime(total):'페이스 '+fmtPace(pace)+'/km'}`;
    if(tb){ const step=k<=10?1:5; let rows=''; for(let x=step;x<k-0.01;x+=step) rows+=`<tr><td>${x}km</td><td>${fmtTime(pace*x)}</td></tr>`; rows+=`<tr><td>골인 ${+k.toFixed(2)}km</td><td>${fmtTime(total)}</td></tr>`; tb.innerHTML=rows; }
    if(pr) pr.innerHTML=[5,10,21.0975,42.195].map(d=>`<tr><td>${dname(d)}</td><td>${fmtTime(total*Math.pow(d/k,1.06))}</td></tr>`).join('');
  }
  $$('[data-km]',root).forEach(c=>c.addEventListener('click',()=>{ $$('[data-km]',root).forEach(x=>x.classList.remove('is-on')); c.classList.add('is-on'); st.km=parseFloat(c.dataset.km); $('.pc-km',root).hidden=st.km!==0; calc(); }));
  $$('[data-mode]',root).forEach(c=>c.addEventListener('click',()=>{ $$('[data-mode]',root).forEach(x=>x.classList.remove('is-on')); c.classList.add('is-on'); st.mode=c.dataset.mode; $('.pc-time',root).hidden=st.mode!=='time'; $('.pc-pace',root).hidden=st.mode!=='pace'; calc(); }));
  $$('input',root).forEach(i=>{ i.addEventListener('input',calc); i.addEventListener('focus',()=>i.select&&i.select()); });
  calc();
}

/* ── 캘린더(.ics) 내보내기 — 서버 없이 브라우저에서 생성 ── */
function icsText(s){ return String(s||'').replace(/\\/g,'\\\\').replace(/\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;'); }
function raceIcs(list){
  const ymd=s=>s.replace(/-/g,''), next=s=>{ const d=pd(s); d.setDate(d.getDate()+1); return iso(d).replace(/-/g,''); };
  const ev=list.map(r=>['BEGIN:VEVENT',`UID:${r.id}@running-plus`,`DTSTAMP:${iso(new Date()).replace(/-/g,'')}T000000Z`,`DTSTART;VALUE=DATE:${ymd(r.start||r.date)}`,`DTEND;VALUE=DATE:${next(r.end||r.date)}`,
    `SUMMARY:${icsText(r.name)}`,r.venue?`LOCATION:${icsText(r.venue)}`:'',r.official?`URL:${r.official}`:'',`DESCRIPTION:${icsText('일정은 바뀔 수 있어요. 공식 홈페이지에서 확인하세요.')}`,'END:VEVENT'].filter(Boolean).join('\r\n'));
  return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Running Plus//KO','CALSCALE:GREGORIAN',...ev,'END:VCALENDAR'].join('\r\n');
}
function downloadText(name,text,mime){ const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([text],{type:mime||'text/plain'})); a.download=name; document.body.appendChild(a); a.click(); setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},500); }
function safeUrl(u){ return /^https?:\/\//i.test(u||'')?u:null; }
const venueQuery = v => { let q=String(v||'').split(/[(（]/)[0].split(/\s[·—–-]\s|·|—/)[0];
  q=q.replace(/\s*(일원|일대|집결|옆.*|[A-Z]구역)$/,'').replace(/\s+/g,' ').trim(); return q||String(v||'').trim(); };
const naverMap = q => 'https://map.naver.com/p/search/'+encodeURIComponent(venueQuery(q));

/* ── 러닝 가이드(블로그): data/blog/index.json · data/blog/<id>.json (build_blog.py 산출물) ── */
const BLOG_LEVELS = ['초급','중급','고급'];
let _blogIdx = null;
function loadBlogIndex(){ return _blogIdx || (_blogIdx = fetch('data/blog/index.json').then(r=>{ if(!r.ok) throw new Error('blog index '+r.status); return r.json(); })); }
function blogRow(p, i){
  return `<a class="ed-guide ed-post-row" href="post.html?id=${encodeURIComponent(p.id)}"><span class="ix">${p2(i!=null?i:p.no)}</span><div><span class="ed-label">${esc(p.level)}${sep}${p.minutes}분</span><h3>${esc(p.title)}</h3><p>${esc(p.summary)}</p></div><span class="ed-arrow" style="color:var(--ink-3)" aria-hidden="true">→</span></a>`;
}
