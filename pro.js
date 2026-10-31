/* Run우리 프로 — 권한 확인(기능 플래그)과 잠금 UI.
   지금은 무료 버전만 출시하므로 launched:false 예요. 이때는 프로 기능이 모두 "준비 중"으로 잠겨 있고,
   ?preview=pro 로 열면 이 기기에서만 미리보기가 열려요(구매 아님). 자세한 설계는 앱 저장소의 PRO_PLAN.md. */
const RWPro = (function(){
  const CFG = {
    launched: false,                 /* 유료 출시 시 true — 이때부터 결제 상태(구독)만 권한으로 인정 */
    showLockedSlots: false,          /* true 면 무료 화면 곳곳에 잠금 자리를 보여 준다 */
    entitlementId: 'pro',            /* RevenueCat entitlement 이름(예정) */
    products: { monthly: 'runwoori_pro_monthly', yearly: 'runwoori_pro_yearly' }   /* Play Console 상품 ID(예정, 아직 등록 안 함) */
  };
  const FEATURES = {
    notify_pro:    { name: '접수 알림 프로',  desc: '접수 오픈 직전·추가 모집·마감 임박 알림, 지역·거리 필터' },
    my_calendar:   { name: '내 대회 캘린더',  desc: '신청한 대회 일정과 전날 준비물·날씨 알림' },
    training_plan: { name: '훈련 플랜',        desc: '목표 대회 날짜에 맞춘 10K·하프·풀 주차별 계획', href: 'plan.html' },
    ad_free:       { name: '광고 제거',        desc: '앱과 웹에서 광고 없이 이용' },
    records:       { name: '기록 관리',        desc: '대회 기록 저장과 개인 최고 기록(PB) 확인', href: 'records.html' }
  };
  const KEY = 'rr_pro_v1', KEY_PREVIEW = 'rr_pro_preview';
  try { if (/[?&]preview=pro\b/.test(location.search)) localStorage.setItem(KEY_PREVIEW, '1'); if (/[?&]preview=off\b/.test(location.search)) localStorage.removeItem(KEY_PREVIEW); } catch (e) {}
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch (e) { return null; } };
  const preview = () => { try { return localStorage.getItem(KEY_PREVIEW) === '1'; } catch (e) { return false; } };
  /* 구독 상태 캐시: { active, until(ms), source:'play', checked(ms) } — 결제 연동 후 refresh() 가 채운다 */
  function isActive(){ const e = read(); return !!(e && e.active && (!e.until || e.until > Date.now())); }
  function has(feature){ if (!FEATURES[feature]) return false; return CFG.launched ? isActive() : preview(); }
  /* 앱(Capacitor)에서 RevenueCat 플러그인이 들어간 빌드일 때만 동작. 지금 빌드엔 없어서 아무것도 하지 않는다. */
  async function refresh(){
    if (!CFG.launched || !window.Capacitor || !Capacitor.nativePromise) return isActive();
    try {
      const r = await Capacitor.nativePromise('Purchases', 'getCustomerInfo', {});
      const ent = r && r.customerInfo && r.customerInfo.entitlements && r.customerInfo.entitlements.active && r.customerInfo.entitlements.active[CFG.entitlementId];
      const exp = ent && ent.expirationDate ? Date.parse(ent.expirationDate) : 0;
      localStorage.setItem(KEY, JSON.stringify({ active: !!ent, until: exp || 0, source: 'play', checked: Date.now() }));
    } catch (e) { /* 오프라인이면 마지막 상태를 유지 */ }
    return isActive();
  }
  /* 잠금 카드: 기능이 잠겨 있을 때 화면 대신(또는 옆에) 보여 준다 */
  function lockCard(feature){
    const f = FEATURES[feature]; if (!f) return '';
    return `<section class="rw-lock" aria-label="${f.name} 잠금"><div class="ed-label">Run우리 프로</div><h2 class="ed-h2" style="margin:8px 0 6px">${f.name}</h2><p class="ed-small" style="line-height:1.7">${f.desc}</p>`
      + (CFG.launched ? `<p style="margin-top:16px"><a class="ed-btn" href="pro.html">프로 알아보기 <span class="ed-arrow">→</span></a></p>`
                      : `<p class="ed-small" style="margin-top:14px"><b>준비 중이에요.</b> 지금은 무료 기능을 그대로 쓸 수 있고, 프로는 나중에 열려요.</p>`)
      + `</section>`;
  }
  /* 한 줄 잠금 자리 (무료 화면 곳곳) — showLockedSlots 가 켜져 있을 때만 */
  function lockSlot(feature){
    if (!CFG.showLockedSlots || has(feature)) return '';
    const f = FEATURES[feature]; return `<p class="ed-small rw-lock-slot"><span aria-hidden="true">🔒</span> ${f.name} · ${CFG.launched ? '<a class="ed-link" href="pro.html">프로</a>' : '준비 중'}</p>`;
  }
  return { CFG, FEATURES, has, isActive, refresh, lockCard, lockSlot, preview };
})();
