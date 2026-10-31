#!/usr/bin/env python3
"""프로(미리보기) 페이지 3개 생성: pro.html · plan.html · records.html  (about.html 의 머리말을 재사용, noindex)
   본문 스크립트는 이 파일에 들어 있다. 실행: python3 tools/make_pro_pages.py"""
import re, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
about = open(os.path.join(ROOT, 'about.html'), encoding='utf8').read()
HEAD0 = about[:about.index('</head>')].replace('<script src="data.js"></script><script src="app.js"></script>', '')

def head(path, title, desc):
    h = HEAD0
    h = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', h)
    for pat in (r'(<meta name="description" content=")[^"]*"', r'(<meta property="og:title" content=")[^"]*"', r'(<meta property="og:description" content=")[^"]*"',
                r'(<meta name="twitter:title" content=")[^"]*"', r'(<meta name="twitter:description" content=")[^"]*"'):
        val = desc if 'description' in pat else title
        h = re.sub(pat, lambda m: m.group(1) + val + '"', h)
    h = h.replace('<meta name="robots" content="index,follow">', '<meta name="robots" content="noindex,follow">')
    h = re.sub(r'<!--CANONICAL:START-->.*?<!--CANONICAL:END-->', '', h, flags=re.S)
    return h + '<script src="data.js"></script><script src="app.js"></script><script src="pro.js"></script></head><body>\n'

PREVIEW = '''<p class="rw-preview" id="pvBar" hidden>프로 미리보기 · 아직 출시 전 기능이에요. 이 기기에서만 열려 있어요.</p>'''

PRO = head('pro.html', 'Run우리 프로 | Run우리', 'Run우리 프로 기능 안내 (준비 중)') + '''
<main class="ed-wrap" id="main">
''' + PREVIEW + '''
<div style="padding:28px var(--page-x) 0"><div class="ed-label accent">Run우리 프로</div><h1 class="ed-h1" style="margin:12px 0 10px">프로 기능</h1>
<p class="ed-lede">지금은 모든 기능을 무료로 쓸 수 있어요. 아래 기능은 나중에 프로로 열릴 예정이에요.</p></div>
<div id="proList" style="margin-top:20px"></div>
</main>
<script>
layout('');
(function(){
  if(RWPro.preview()) document.getElementById('pvBar').hidden=false;
  document.getElementById('proList').innerHTML=Object.keys(RWPro.FEATURES).map(function(k,i){var f=RWPro.FEATURES[k];
    var on=RWPro.has(k);
    return '<article class="ed-course"><span class="ix">'+String(i+1).padStart(2,'0')+'</span><div><h3>'+f.name+'</h3><p class="ed-meta">'+f.desc+'</p>'
      +(on&&f.href?'<a class="ed-link ed-small" style="display:inline-block;margin-top:6px" href="'+f.href+'">열기 →</a>':'<p class="ed-small" style="margin-top:6px">'+(on?'사용 중':'준비 중')+'</p>')+'</div></article>';}).join('');
})();
</script></body></html>
'''

PLAN = head('plan.html', '훈련 플랜 | Run우리', '목표 대회 날짜에 맞춘 주차별 훈련 계획 예시') + '''
<main class="ed-wrap" id="main">
''' + PREVIEW + '''
<div style="padding:28px var(--page-x) 0"><div class="ed-label accent">Run우리 프로</div><h1 class="ed-h1" style="margin:12px 0 10px">훈련 플랜</h1>
<p class="ed-lede">목표 대회 날짜까지 주차별로 달릴 거리를 정리해요. 일반적인 예시이고, 몸 상태에 맞게 줄이거나 쉬어 가세요.</p></div>
<div id="lock"></div>
<div id="tool" hidden>
<section style="padding:0 var(--page-x)">
  <div class="rw-form">
    <div class="full"><label>목표 종목</label><div class="rw-seg" id="segDist"><button type="button" data-k="10k">10K</button><button type="button" data-k="half" class="is-on">하프</button><button type="button" data-k="full">풀</button></div></div>
    <div><label for="raceDate">대회 날짜</label><input class="ed-input" type="date" id="raceDate"></div>
    <div id="savedBox" hidden><label for="savedSel">저장한 대회에서 고르기</label><select id="savedSel"><option value="">선택</option></select></div>
    <div><label>주당 러닝 횟수</label><div class="rw-seg" id="segRuns"><button type="button" data-k="3">3회</button><button type="button" data-k="4" class="is-on">4회</button><button type="button" data-k="5">5회</button></div></div>
    <div><label for="baseKm">요즘 일주일에 달리는 거리(km)</label><input class="ed-input" type="number" id="baseKm" min="5" max="80" step="1" value="20" inputmode="numeric"></div>
    <div class="full"><button type="button" class="ed-btn" id="make">계획 만들기 <span class="ed-arrow">→</span></button></div>
  </div>
</section>
<section id="out" style="padding:28px var(--page-x) 0"></section>
<p class="ed-small" style="padding:22px var(--page-x) 0;line-height:1.8">이 계획은 일반적으로 알려진 훈련 원칙(주간 거리를 조금씩 늘리고, 4주마다 한 번 줄이고, 대회 직전에는 줄이는 방식)을 단순하게 옮긴 예시예요. 개인의 건강 상태와 경험을 반영하지 않으며, 의학적·전문적 조언이 아니에요. 통증이나 지병이 있다면 무리하지 말고 전문가와 상담하세요.</p>
</div>
</main>
<script>
layout('');
(function(){
  if(RWPro.preview()) document.getElementById('pvBar').hidden=false;
  if(!RWPro.has('training_plan')){ document.getElementById('lock').innerHTML=RWPro.lockCard('training_plan'); return; }
  document.getElementById('tool').hidden=false;
  var TPL={'10k':{label:'10K',km:10,weeks:8,cap:40,longCap:14,taper:[0.75,0.5],warn:0},
           'half':{label:'하프',km:21.0975,weeks:12,cap:55,longCap:20,taper:[0.75,0.5],warn:25},
           'full':{label:'풀코스',km:42.195,weeks:16,cap:70,longCap:32,taper:[0.8,0.6,0.4],warn:40}};
  var KEY='rr_plan_v1', st=load()||{dist:'half',runs:4,base:20,date:'',done:{}};
  function load(){ try{return JSON.parse(localStorage.getItem(KEY));}catch(e){return null;} }
  function save(){ localStorage.setItem(KEY,JSON.stringify(st)); }
  function mondayOf(d){ var x=new Date(d.getFullYear(),d.getMonth(),d.getDate()); x.setDate(x.getDate()-((x.getDay()+6)%7)); return x; }
  function mmdd(d){ return (d.getMonth()+1)+'.'+d.getDate(); }
  function seg(id,key){ var el=document.getElementById(id); Array.prototype.forEach.call(el.children,function(b){ b.classList.toggle('is-on',String(st[key])===b.dataset.k); b.onclick=function(){ st[key]=b.dataset.k; if(key==='runs') st.runs=+st.runs; seg(id,key); }; }); }
  seg('segDist','dist'); seg('segRuns','runs');
  var dEl=document.getElementById('raceDate'), bEl=document.getElementById('baseKm'); dEl.value=st.date||''; bEl.value=st.base;
  var q=(location.search.match(/[?&]date=(\\d{4}-\\d\\d-\\d\\d)/)||[])[1]; if(q&&!st.date){ dEl.value=q; }
  RACES_READY.then(function(){ var l=allRaces().filter(function(r){return favs.has(r.id)&&r.d>=14;}).sort(function(a,b){return a.d-b.d;});
    if(!l.length) return; var sel=document.getElementById('savedSel'); document.getElementById('savedBox').hidden=false;
    l.forEach(function(r){ var o=document.createElement('option'); o.value=r.date; o.textContent=r.date.slice(5).replace('-','.')+' '+r.name; sel.appendChild(o); });
    sel.onchange=function(){ if(sel.value) dEl.value=sel.value; }; });

  function build(){
    var T=TPL[st.dist], today=new Date(); today.setHours(0,0,0,0);
    var rd=dEl.value?new Date(dEl.value+'T00:00:00'):null, base=Math.max(5,Math.min(80,Math.round(+bEl.value)||0)), runs=st.runs;
    var out=document.getElementById('out');
    if(!rd||rd<=today){ out.innerHTML='<div class="ed-empty">오늘 이후의 대회 날짜를 골라 주세요.</div>'; return; }
    st.date=dEl.value; st.base=base; save();
    var m0=mondayOf(today), m1=mondayOf(rd), N=Math.round((m1-m0)/604800000)+1;
    if(N<4){ out.innerHTML='<div class="ed-empty">대회까지 남은 기간이 너무 짧아요(4주 미만). 이 기간에는 새 계획을 세우기보다 지금 달리는 양을 유지하고 컨디션을 관리하는 편이 안전해요.</div>'; return; }
    var tp=T.taper, nT=tp.length, nBase=Math.max(0,N-T.weeks), nBuild=N-nT-nBase;
    var peakCap=Math.min(T.cap, Math.round(base*(st.dist==='full'?2.2:2.0)));
    peakCap=Math.max(peakCap,base);
    var rows=[], cur=base, peak=base, j=0, w;
    for(w=0;w<N;w++){
      var phase, vol;
      if(w<nBase){ phase='기초 다지기'; vol=base; }
      else if(w<nBase+nBuild){ var b=w-nBase; var down=(b+1)%4===0&&b<nBuild-1;
        if(b>0&&!down){ var prevFull=cur; cur=Math.min(peakCap,Math.max(cur,Math.round(cur*1.08+0.4))); if(cur>prevFull*1.12) cur=Math.round(prevFull*1.1); }
        if(down){ phase='휴식 주'; vol=Math.round(cur*0.75); } else { phase=b===0?'빌드 시작':'빌드'; vol=cur; peak=Math.max(peak,cur); } }
      else { var ti=w-nBase-nBuild; phase=ti===nT-1?'대회 주':'테이퍼(줄이기)'; vol=Math.round(peak*tp[ti]); }
      rows.push({w:w,phase:phase,vol:vol});
    }
    var h='<div class="ed-label nocase">'+T.label+' · '+N+'주 계획 · 정점 주간 거리 약 '+peak+'km</div>';
    var warns=[];
    if(nBuild<Math.min(6,T.weeks-nT)) warns.push('남은 기간이 권장 기간('+T.weeks+'주)보다 짧아서 늘리는 구간이 짧아요. 목표 기록보다 완주와 부상 예방을 우선하세요.');
    if(T.warn&&peak<T.warn) warns.push('이 계획의 정점 주간 거리('+peak+'km)는 '+T.label+' 준비로는 적은 편일 수 있어요. 대회 날짜를 늦추거나 더 짧은 종목을 먼저 고려해 보세요.');
    if(warns.length) h+='<p class="ed-note" style="margin:12px 0 0">'+warns.join('<br>')+'</p>';
    h+='<table class="rw-weeks"><thead><tr><th>주</th><th>기간</th><th>합계</th><th>구성</th></tr></thead><tbody>';
    rows.forEach(function(r){
      var ws=new Date(m0); ws.setDate(ws.getDate()+7*r.w); var we=new Date(ws); we.setDate(we.getDate()+6);
      var isRace=r.w===N-1, comp, note='';
      if(isRace){ comp='가벼운 러닝 2회 합계 약 '+Math.max(5,Math.round(r.vol*0.5))+'km + 대회('+T.label+')'; note='대회 전날과 전전날은 쉬거나 아주 가볍게.'; }
      else { var long=Math.min(T.longCap,Math.max(3,Math.round(r.vol*0.35))), rest=Math.max(0,r.vol-long), n=runs-1, each=Math.max(2,Math.round(rest/n*2)/2);
        comp='롱런 '+long+'km + 쉬운 러닝 '+n+'회(회당 약 '+each+'km)';
        note={'기초 다지기':'지금 달리는 양을 유지해요.','빌드 시작':'대화가 가능한 속도로.','빌드':'쉬운 속도 위주. 원하면 짧은 스트라이드 4~6회를 한 번만.','휴식 주':'몸이 회복하는 주예요. 거리를 줄여요.','테이퍼(줄이기)':'거리를 줄여 컨디션을 올려요.'}[r.phase]||''; }
      var done=st.done[r.w]?' checked':'';
      h+='<tr'+(isRace?' class="is-race"':'')+'><td class="num">'+(r.w+1)+'</td><td class="num">'+mmdd(ws)+'~'+mmdd(we)+'</td><td class="num">'+(isRace?'':r.vol+'km')+'</td><td>'+r.phase+(isRace?' · '+mmdd(rd)+'(대회일)':'')+'<br><span class="ed-small">'+comp+(note?'<br>'+note:'')+'</span><br><label class="ed-small" style="display:inline-flex;gap:6px;align-items:center;margin-top:4px"><input type="checkbox" data-w="'+r.w+'"'+done+'> 완료</label></td></tr>';
    });
    h+='</tbody></table>';
    out.innerHTML=h;
    Array.prototype.forEach.call(out.querySelectorAll('input[data-w]'),function(c){ c.onchange=function(){ if(c.checked) st.done[c.dataset.w]=1; else delete st.done[c.dataset.w]; save(); }; });
  }
  document.getElementById('make').onclick=build;
  if(st.date) build();
})();
</script></body></html>
'''

REC = head('records.html', '기록 관리 | Run우리', '대회 기록을 저장하고 개인 최고 기록(PB)을 확인해요') + '''
<main class="ed-wrap" id="main">
''' + PREVIEW + '''
<div style="padding:28px var(--page-x) 0"><div class="ed-label accent">Run우리 프로</div><h1 class="ed-h1" style="margin:12px 0 10px">기록 관리</h1>
<p class="ed-lede">완주한 대회 기록을 저장하고 종목별 개인 최고 기록(PB)을 확인해요. 기록은 이 기기에만 저장돼요.</p></div>
<div id="lock"></div>
<div id="tool" hidden>
<section style="padding:0 var(--page-x)">
  <div class="rw-form">
    <div class="full"><label for="rName">대회 이름</label><input class="ed-input" id="rName" maxlength="60" autocomplete="off"></div>
    <div><label for="rDate">날짜</label><input class="ed-input" type="date" id="rDate"></div>
    <div><label for="rDist">종목</label><select id="rDist"><option value="5k">5K</option><option value="10k">10K</option><option value="half">하프</option><option value="full">풀</option><option value="custom">직접 입력</option></select></div>
    <div id="kmBox" hidden><label for="rKm">거리(km)</label><input class="ed-input" type="number" id="rKm" step="0.01" min="0.5" inputmode="decimal"></div>
    <div><label>기록 (시 · 분 · 초)</label><div class="rw-row2" style="grid-template-columns:1fr 1fr 1fr"><input class="ed-input" id="rH" inputmode="numeric" placeholder="시" aria-label="시"><input class="ed-input" id="rM" inputmode="numeric" placeholder="분" aria-label="분"><input class="ed-input" id="rS" inputmode="numeric" placeholder="초" aria-label="초"></div></div>
    <div class="full"><label for="rMemo">메모 (선택)</label><input class="ed-input" id="rMemo" maxlength="80" autocomplete="off"></div>
    <div class="full"><button type="button" class="ed-btn" id="rAdd">기록 저장 <span class="ed-arrow">→</span></button></div>
  </div>
</section>
<section style="padding:30px var(--page-x) 0"><div class="ed-label">개인 최고 기록(PB)</div><div id="pbs" style="margin-top:8px"></div></section>
<section style="padding:30px var(--page-x) 0"><div class="ed-label">전체 기록</div><div id="list" style="margin-top:6px;border-top:var(--line) solid var(--rule)"></div>
<p class="ed-small" style="margin-top:14px;display:flex;flex-wrap:wrap;gap:6px 18px"><button type="button" class="ed-link ed-textbtn" id="rCsv">CSV로 복사</button></p></section>
</div>
</main>
<script>
layout('');
(function(){
  if(RWPro.preview()) document.getElementById('pvBar').hidden=false;
  if(!RWPro.has('records')){ document.getElementById('lock').innerHTML=RWPro.lockCard('records'); return; }
  document.getElementById('tool').hidden=false;
  var KEY='rr_records_v1', D={'5k':5,'10k':10,'half':21.0975,'full':42.195}, N={'5k':'5K','10k':'10K','half':'하프','full':'풀','custom':'기타'};
  function load(){ try{return JSON.parse(localStorage.getItem(KEY))||[];}catch(e){return [];} }
  function save(a){ localStorage.setItem(KEY,JSON.stringify(a)); }
  var $=function(s){return document.querySelector(s);};
  $('#rDist').onchange=function(){ $('#kmBox').hidden=$('#rDist').value!=='custom'; };
  function pbMap(a){ var m={}; a.forEach(function(r){ if(r.dist==='custom') return; if(!m[r.dist]||r.sec<m[r.dist].sec) m[r.dist]=r; }); return m; }
  function draw(){
    var a=load().sort(function(x,y){return x.date<y.date?1:-1;}), pb=pbMap(a);
    $('#pbs').innerHTML=Object.keys(D).map(function(k){ var r=pb[k]; return '<div class="rw-rec"><span class="ed-label">'+N[k]+'</span><span>'+(r?esc(r.name)+' <span class="ed-small">'+r.date+'</span>':'<span class="ed-small">아직 기록이 없어요</span>')+'</span><b>'+(r?fmtTime(r.sec):'–')+'</b></div>'; }).join('');
    $('#list').innerHTML=a.length?a.map(function(r){ var isPb=r.dist!=='custom'&&pb[r.dist]&&pb[r.dist].id===r.id;
      return '<div class="rw-rec"><span class="ed-label">'+N[r.dist]+'</span><span>'+esc(r.name)+(isPb?'<span class="rw-pb">PB</span>':'')+'<br><span class="ed-small">'+r.date+' · 페이스 '+fmtPace(r.sec/r.km)+'/km'+(r.memo?' · '+esc(r.memo):'')+'</span></span><span style="text-align:right"><b>'+fmtTime(r.sec)+'</b><br><button type="button" class="ed-link ed-textbtn ed-small" data-del="'+r.id+'">삭제</button></span></div>'; }).join('')
      :'<div class="ed-empty">저장한 기록이 없어요.</div>';
    Array.prototype.forEach.call(document.querySelectorAll('[data-del]'),function(b){ b.onclick=function(){ if(!confirm('이 기록을 삭제할까요?')) return; save(load().filter(function(r){return r.id!==b.dataset.del;})); draw(); }; });
  }
  $('#rAdd').onclick=function(){
    var name=$('#rName').value.trim(), date=$('#rDate').value, dist=$('#rDist').value, km=dist==='custom'?parseFloat($('#rKm').value):D[dist];
    var sec=(parseInt($('#rH').value)||0)*3600+(parseInt($('#rM').value)||0)*60+(parseInt($('#rS').value)||0);
    if(!name||!date||!km||km<=0||sec<=0){ toast('이름, 날짜, 거리, 기록을 모두 입력해 주세요'); return; }
    if(date>iso(new Date())){ toast('오늘 이후 날짜는 기록으로 저장할 수 없어요'); return; }
    var a=load(); a.push({id:'r'+Date.now().toString(36),name:name,date:date,dist:dist,km:km,sec:sec,memo:$('#rMemo').value.trim()}); save(a);
    ['#rName','#rH','#rM','#rS','#rMemo'].forEach(function(s){$(s).value='';}); toast('기록을 저장했어요'); draw();
  };
  $('#rCsv').onclick=function(){ var a=load(); var csv='날짜,대회,종목,거리(km),기록,메모\\n'+a.map(function(r){ return [r.date,'"'+r.name.replace(/"/g,'""')+'"',N[r.dist],r.km,fmtTime(r.sec),'"'+(r.memo||'').replace(/"/g,'""')+'"'].join(','); }).join('\\n');
    (navigator.clipboard?navigator.clipboard.writeText(csv):Promise.reject()).then(function(){toast('CSV를 복사했어요');},function(){toast('복사하지 못했어요');}); };
  draw();
})();
</script></body></html>
'''
for name, body in (('pro.html', PRO), ('plan.html', PLAN), ('records.html', REC)):
    open(os.path.join(ROOT, name), 'w', encoding='utf8').write(body)
print('wrote pro.html plan.html records.html')
