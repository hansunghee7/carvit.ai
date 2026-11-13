/* 홈 히어로 '무료 가이드 신청' 이메일 팝업 (마중물 T1, 지투 요청 2026-11-12).
   이메일과 동의만 받아 mcp.carvit.ai 의 POST /guide-request 로 보낸다(super-carvit PR 1071).
   눈에 안 보이는 칸(website)은 봇 거르기용이라 사람이 채우지 않는다. 쿠키·저장소는 쓰지 않는다. */
(function () {
  var ko = document.documentElement.lang === 'ko';
  var T = ko ? {
    title: '무료 가이드 신청',
    desc: '이메일을 남기면 선정된 분께 무료 가이드 제작 안내를 보내드립니다.',
    email: '이메일', consent: '무료 가이드 안내를 위해 이메일을 수집하고 180일간 보관하는 데 동의합니다.',
    policy: '개인정보 처리방침', policyUrl: '/ko/privacy/', send: '신청하기', close: '닫기',
    bad: '이메일 주소를 확인해 주세요.', need: '동의가 필요합니다.',
    fail: '지금은 접수하지 못했습니다. 잠시 뒤 다시 시도해 주세요.', rate: '요청이 많습니다. 잠시 뒤 다시 시도해 주세요.',
    doneT: '신청이 접수되었습니다', doneD: '선정되면 남기신 이메일로 안내를 보내드립니다.', src: 'home-ko'
  } : {
    title: 'Get a free guide',
    desc: 'Leave your email and we will send setup details to those selected for a free guide.',
    email: 'Email', consent: 'I agree to Carvit collecting my email for this and keeping it for 180 days.',
    policy: 'Privacy Policy', policyUrl: '/privacy/', send: 'Apply', close: 'Close',
    bad: 'Please check your email address.', need: 'Consent is required.',
    fail: 'We could not save your request. Please try again shortly.', rate: 'Too many requests. Please try again shortly.',
    doneT: 'Your request is in', doneD: 'If you are selected, we will email you at the address you left.', src: 'home-en'
  };
  var ENDPOINT = 'https://mcp.carvit.ai/guide-request';

  var css = document.createElement('style');
  css.textContent =
    '.btn.green{background:#16a34a;color:#fff}' +
    '.gp-bg{position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.6);display:none;align-items:center;justify-content:center;padding:16px}' +
    '.gp-bg.open{display:flex}' +
    '.gp{background:#fff;color:#000;border-radius:12px;width:100%;max-width:420px;padding:28px 24px;position:relative;font-size:14px;line-height:22px}' +
    '.gp h2{font-size:22px;line-height:1.3;margin:0 28px 8px 0}' +
    '.gp p{color:var(--ink-muted,rgba(0,0,0,.6));margin:0 0 16px}' +
    '.gp label.f{display:block;font-weight:500;margin-bottom:6px}' +
    '.gp input[type=email]{width:100%;height:44px;border:1px solid rgba(0,0,0,.2);border-radius:8px;padding:0 12px;font:inherit;font-size:16px;color:#000;background:#fff}' +
    '.gp .ck{display:flex;gap:8px;align-items:flex-start;margin:14px 0;font-size:13px;line-height:20px}' +
    '.gp .ck input{margin-top:3px;flex:none}' +
    '.gp .ck a{text-decoration:underline}' +
    '.gp .err{color:#b91c1c;min-height:20px;margin:0 0 8px;font-size:13px}' +
    '.gp .btn{width:100%;height:44px}' +
    '.gp .btn[disabled]{opacity:.4;cursor:default}' +
    '.gp .x{position:absolute;top:10px;right:10px;width:36px;height:36px;border:0;background:none;font-size:24px;line-height:1;cursor:pointer;color:#000}' +
    '.gp .hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}';
  document.head.appendChild(css);

  var bg = document.createElement('div');
  bg.className = 'gp-bg';
  bg.innerHTML =
    '<div class="gp" role="dialog" aria-modal="true" aria-labelledby="gp-t">' +
    '<button type="button" class="x" aria-label="' + T.close + '">&times;</button>' +
    '<form novalidate>' +
    '<h2 id="gp-t">' + T.title + '</h2><p>' + T.desc + '</p>' +
    '<label class="f" for="gp-e">' + T.email + '</label>' +
    '<input id="gp-e" type="email" name="email" autocomplete="email" inputmode="email" required>' +
    '<div class="hp" aria-hidden="true"><input type="text" name="website" tabindex="-1" autocomplete="off"></div>' +
    '<label class="ck"><input type="checkbox" name="consent"><span>' + T.consent + ' <a href="' + T.policyUrl + '" target="_blank" rel="noopener">' + T.policy + '</a></span></label>' +
    '<p class="err" role="alert"></p>' +
    '<button type="submit" class="btn green" disabled>' + T.send + '</button>' +
    '</form>' +
    '<div class="done" hidden><h2>' + T.doneT + '</h2><p>' + T.doneD + '</p><button type="button" class="btn black x2">' + T.close + '</button></div>' +
    '</div>';
  document.body.appendChild(bg);

  var form = bg.querySelector('form'), em = form.email, ck = form.consent, btn = form.querySelector('.btn'),
      err = bg.querySelector('.err'), done = bg.querySelector('.done'), opener = null, busy = false;

  function sync() { btn.disabled = busy || !ck.checked; }
  function open(e) { opener = e; bg.classList.add('open'); em.focus(); }
  function close() { bg.classList.remove('open'); if (opener) opener.focus(); }
  ck.addEventListener('change', sync);
  bg.querySelector('.x').addEventListener('click', close);
  bg.querySelector('.x2').addEventListener('click', close);
  bg.addEventListener('click', function (e) { if (e.target === bg) close(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && bg.classList.contains('open')) close(); });
  Array.prototype.forEach.call(document.querySelectorAll('[data-guide-open]'), function (b) {
    b.addEventListener('click', function () { open(b); });
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    err.textContent = '';
    if (!ck.checked) { err.textContent = T.need; return; }
    var v = em.value.trim();
    if (!/^[^\s@,]+@[^\s@,]+\.[^\s@,]{2,}$/.test(v)) { err.textContent = T.bad; em.focus(); return; }
    busy = true; sync();
    fetch(ENDPOINT, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: v, consent: true, source: T.src, website: form.website.value })
    }).then(function (r) {
      busy = false; sync();
      if (r.ok) { form.hidden = true; done.hidden = false; return; }
      err.textContent = r.status === 400 ? T.bad : r.status === 429 ? T.rate : T.fail;
    }).catch(function () { busy = false; sync(); err.textContent = T.fail; });
  });
})();
