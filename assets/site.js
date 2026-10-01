/* 언어 선택 기억·자동 이동. 백서 페이지 인라인 스크립트를 공용 파일로 옮김(2026-10-01) */
(function () {
  try {
    var KEY = 'carvit-lang';
    var links = document.querySelectorAll('a.lang');
    for (var i = 0; i < links.length; i++) {
      links[i].addEventListener('click', function () { localStorage.setItem(KEY, this.getAttribute('data-lang')); });
    }
    // 자동 이동은 영문 첫 화면(/)에서만, 한국어를 고른 적이 있거나 브라우저 언어가 한국어일 때. /ko/ 직접 접속은 절대 이동하지 않는다(검색 로봇·공유 링크 보호).
    if (document.documentElement.lang === 'en' && !location.hash) {
      var saved = localStorage.getItem(KEY);
      var want = saved || ((navigator.language || 'en').toLowerCase().indexOf('ko') === 0 ? 'ko' : 'en');
      if (want === 'ko') { location.replace(document.querySelector('a.lang').getAttribute('href')); }
    }
  } catch (e) {}
})();
