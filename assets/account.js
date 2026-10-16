/* 로그인 뒤 머리의 계정 메뉴(UX_GUIDE_CARVIT 1.39, R-75 2026-10-16: 앱에서 로그인했는데 홈 머리에 'Log in'이 보인다는 사장님 실측).
   앱(mcp.carvit.ai)이 로그인 때 .carvit.ai에 붙이는 신원 없는 표시 쿠키 carvit_li=1이 있을 때만 앱의 세션 확인 끝점(/session/me, carvit.ai만 허용)에 묻는다.
   확인되면 머리의 로그인 버튼 자리를 이메일 첫 글자 원(누르는 영역 44px) 하나로 바꾸고, 메뉴에 이메일 전체·대시보드·언어·로그아웃을 이 순서로 둔다.
   쿠키가 없거나 확인에 실패하면 아무것도 바꾸지 않는다(로그인 버튼 그대로). 이메일은 응답 본문으로만 받고 쿠키·주소에 싣지 않는다.
   메뉴 동작은 앱 머리와 같은 W3C 메뉴 버튼 패턴(Enter·Space·방향키·Home·End·Esc). */
(function () {
  try {
    if (!/(?:^|; )carvit_li=1(?:;|$)/.test(document.cookie)) return;
    var APP = 'https://mcp.carvit.ai';
    fetch(APP + '/session/me', { credentials: 'include', cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) { if (j && j['in'] === true && j.email) render(String(j.email)); })
      .catch(function () {});

    function render(email) {
      var nav = document.querySelector('nav');
      if (!nav) return;
      var login = nav.querySelector('a.login') || nav.querySelector('a[href="' + APP + '/login"]');
      if (!login || document.getElementById('cvam-btn')) return;
      var ko = document.documentElement.lang === 'ko';
      var T = ko ? { account: '계정 메뉴', dash: '대시보드', out: '로그아웃' } : { account: 'Account menu', dash: 'Dashboard', out: 'Log out' };
      var dark = !!login.closest('.hero');  // 홈은 검은 판 위 머리
      var lang = nav.querySelector('a.lang');

      if (!document.getElementById('cvam-css')) {
        var st = document.createElement('style');
        st.id = 'cvam-css';
        st.textContent =
          '.cvam{position:relative;display:inline-flex;margin-left:4px}' +
          '.cvam-btn{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;padding:0;border:0;border-radius:50%;background:none;cursor:pointer}' +
          '.cvam-c{display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:50%;background:#000;color:#fff;font:600 14px/1 Geist,ui-sans-serif,system-ui,sans-serif}' +
          '.cvam.dark .cvam-c{background:#fff;color:#000}' +
          '.cvam-btn:focus-visible{outline:2px solid currentColor;outline-offset:1px}' +
          '.cvam-menu{position:absolute;right:0;top:calc(100% + 4px);z-index:50;min-width:200px;max-width:min(300px,calc(100vw - 32px));padding:4px;background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:10px;box-shadow:0 4px 16px rgba(0,0,0,.08);display:flex;flex-direction:column;text-align:left}' +
          '.cvam-menu[hidden]{display:none}' +
          '.cvam-mail{padding:8px 12px;font-size:12px;color:rgba(0,0,0,.6);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-bottom:1px solid rgba(0,0,0,.12);margin-bottom:4px}' +
          '.cvam-menu a{display:flex;align-items:center;min-height:44px;padding:0 12px;border-radius:6px;font-size:14px;color:#000;text-decoration:none;background:none;border:0;margin:0}' +
          '.cvam-menu a:hover,.cvam-menu a:focus-visible{background:rgba(0,0,0,.04);outline:none}';
        document.head.appendChild(st);
      }

      var wrap = document.createElement('div');
      wrap.className = 'cvam' + (dark ? ' dark' : '');
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'cvam-btn'; b.id = 'cvam-btn';
      b.setAttribute('aria-haspopup', 'menu'); b.setAttribute('aria-expanded', 'false');
      b.setAttribute('aria-controls', 'cvam-menu'); b.setAttribute('aria-label', T.account); b.title = email;
      var c = document.createElement('span'); c.className = 'cvam-c'; c.textContent = (email.trim().charAt(0) || '?').toUpperCase();
      b.appendChild(c);
      var m = document.createElement('div');
      m.className = 'cvam-menu'; m.id = 'cvam-menu'; m.setAttribute('role', 'menu'); m.setAttribute('aria-label', T.account); m.hidden = true;
      var mail = document.createElement('div'); mail.className = 'cvam-mail'; mail.setAttribute('role', 'none'); mail.title = email; mail.textContent = email;
      m.appendChild(mail);
      function item(text, href) {
        var a = document.createElement('a'); a.setAttribute('role', 'menuitem'); a.tabIndex = -1; a.href = href; a.textContent = text;
        m.appendChild(a); return a;
      }
      item(T.dash, APP + '/dashboard');
      if (lang) {
        var li = item(lang.textContent.trim(), lang.getAttribute('href'));
        var to = lang.getAttribute('data-lang') || (lang.getAttribute('hreflang') || '').slice(0, 2);
        li.addEventListener('click', function () {
          if (to !== 'ko' && to !== 'en') return;
          var d = /(^|\.)carvit\.ai$/.test(location.hostname) ? '; Domain=.carvit.ai' : '';
          document.cookie = 'carvit_lang=' + to + d + '; Path=/; Max-Age=31536000; SameSite=Lax' + (location.protocol === 'https:' ? '; Secure' : '');
          try { localStorage.setItem('carvit-lang', to); } catch (e) {}
        });
        lang.style.display = 'none';  // 로그인 뒤에는 언어도 메뉴 안으로(오른쪽 끝 요소 하나)
      }
      item(T.out, APP + '/logout');
      wrap.appendChild(b); wrap.appendChild(m);
      login.parentNode.replaceChild(wrap, login);

      function items() { return Array.prototype.slice.call(m.querySelectorAll('[role=menuitem]')); }
      function open(f) { m.hidden = false; b.setAttribute('aria-expanded', 'true'); var i = items(); if (f && i.length) i[f === 'last' ? i.length - 1 : 0].focus(); }
      function close(back) { m.hidden = true; b.setAttribute('aria-expanded', 'false'); if (back) b.focus(); }
      b.addEventListener('click', function () { m.hidden ? open('first') : close(true); });
      b.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown') { e.preventDefault(); open('first'); } else if (e.key === 'ArrowUp') { e.preventDefault(); open('last'); }
      });
      m.addEventListener('keydown', function (e) {
        var i = items(), k = i.indexOf(document.activeElement);
        if (e.key === 'Escape') { e.preventDefault(); close(true); }
        else if (e.key === 'ArrowDown') { e.preventDefault(); i[(k + 1) % i.length].focus(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); i[(k - 1 + i.length) % i.length].focus(); }
        else if (e.key === 'Home') { e.preventDefault(); i[0].focus(); }
        else if (e.key === 'End') { e.preventDefault(); i[i.length - 1].focus(); }
        else if (e.key === 'Tab') { close(false); }
      });
      document.addEventListener('click', function (e) { if (!m.hidden && !m.contains(e.target) && !b.contains(e.target)) close(false); });

      // 로그인한 사람용 본문 버튼(시작하기 → 연결 방법 등)
      var MAP = { '무료로 시작하기': ['연결 방법 열기', 'connect'], 'Start free': ['Open the Connect screen', 'connect'] };
      var plain = document.querySelectorAll('a[href="' + APP + '/login"]');
      for (var p = 0; p < plain.length; p++) {
        var t = MAP[plain[p].textContent.trim()];
        if (t) { plain[p].textContent = t[0]; plain[p].setAttribute('href', APP + '/' + t[1]); }
      }
      var els = document.querySelectorAll('[data-li-text]');
      for (var q = 0; q < els.length; q++) {
        els[q].textContent = els[q].getAttribute('data-li-text');
        if (els[q].getAttribute('data-li-href')) els[q].setAttribute('href', els[q].getAttribute('data-li-href'));
      }
    }
  } catch (e) {}
})();
