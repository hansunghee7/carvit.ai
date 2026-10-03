/* 언어 선택 기억·자동 이동. 백서 페이지 인라인 스크립트를 공용 파일로 옮김(2026-10-01) */
(function () {
  try {
    var KEY = 'carvit-lang';
    // 쿠키 carvit_lang은 상위 도메인(.carvit.ai)에 심어 앱(mcp.carvit.ai)도 같은 값을 읽는다(2026-10-03 P10). localStorage는 도메인별이라 앱이 못 본다.
    function getCookie() {
      var m = document.cookie.match(/(?:^|; )carvit_lang=(ko|en)/);
      return m ? m[1] : null;
    }
    function setLang(v) {
      try { localStorage.setItem(KEY, v); } catch (e) {}
      var d = /(^|\.)carvit\.ai$/.test(location.hostname) ? '; Domain=.carvit.ai' : '';  // 미리보기·로컬 주소에서는 도메인 생략
      document.cookie = 'carvit_lang=' + v + d + '; Path=/; Max-Age=31536000; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');
    }
    var links = document.querySelectorAll('a.lang');
    for (var i = 0; i < links.length; i++) {
      links[i].addEventListener('click', function () { setLang(this.getAttribute('data-lang')); });
    }
    // 자동 이동은 영문 첫 화면(/)에서만, 쿠키(없으면 localStorage)로 한국어를 고른 적이 있거나 브라우저 언어가 한국어일 때. /ko/ 직접 접속은 절대 이동하지 않는다(검색 로봇·공유 링크 보호).
    var here = document.documentElement.lang === 'ko' ? 'ko' : 'en';
    var want = null;
    // 영문 글 주소(/tech-report/...)를 한국어 브라우저에서 열어도 한국어 페이지로 보내지 않는다(2026-10-03: 영문 글 제목이 한글로 나온다는 신고의 원인. 주석은 '/에서만'이었는데 코드는 모든 영문 페이지에서 이동했다).
    if (here === 'en' && !location.hash && location.pathname === '/') {
      var saved = getCookie() || localStorage.getItem(KEY);
      want = saved || ((navigator.language || 'en').toLowerCase().indexOf('ko') === 0 ? 'ko' : 'en');
      if (want === 'ko') { location.replace(document.querySelector('a.lang').getAttribute('href')); return; }
    }
    setLang(here);  // 이동하지 않고 이 언어 페이지에 머무를 때만 심는다
  } catch (e) {}
})();

/* 휴대폰 햄버거(하위 페이지 공용) */
(function () {
  var b = document.getElementById('burger'), s = document.getElementById('sheet');
  if (!b || !s || b.dataset.bound || !b.closest('.site-nav')) return;  // 홈은 자체 스크립트
  b.dataset.bound = '1';
  var open = b.getAttribute('aria-label'), close = b.getAttribute('data-close') || open;
  b.addEventListener('click', function () {
    var o = s.classList.toggle('open');
    b.setAttribute('aria-expanded', o); b.setAttribute('aria-label', o ? close : open);
  });
})();
