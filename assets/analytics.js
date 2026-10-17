/* 방문 분석: Microsoft Clarity(프로젝트 Carvit 20261018). 사장님 결정 2026-10-18(A-88 "붙인다").
   왜: carvit.ai는 방문자가 어디서 막히는지 전혀 몰랐다. Clarity는 무료이고, 히트맵·세션 녹화로 막히는 곳을 눈으로 보며,
   에이전트가 예측한 방향을 실제 방문자 행동과 대조하는 무료 대조군이 된다(Prolific 유료 파일럿 대신, A-115).
   입력칸 내용은 Clarity 기본 마스킹으로 가려진다. 우리 팀 방문은 ?internal=1로 한 번 표시하면 그 브라우저에서 수집하지 않는다(?internal=0으로 해제). */
(function () {
  try {
    var q = location.search;
    if (/[?&]internal=1(&|$)/.test(q)) localStorage.setItem('cv_internal', '1');
    if (/[?&]internal=0(&|$)/.test(q)) localStorage.removeItem('cv_internal');
    if (localStorage.getItem('cv_internal') === '1') return;
  } catch (e) {}
  if (location.hostname !== 'carvit.ai') return;  /* 미리보기·로컬에서는 수집하지 않는다 */
  (function (c, l, a, r, i, t, y) {
    c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
    t = l.createElement(r); t.async = 1; t.src = 'https://www.clarity.ms/tag/' + i;
    y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
  })(window, document, 'clarity', 'script', 'yz6zngkgoi');
})();
