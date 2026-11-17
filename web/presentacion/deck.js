/* UNABot — mecánica del deck. Sin dependencias, sin handlers inline (CSP estricta). */
(function () {
  'use strict';
  var W = 1920, H = 1080;
  var stage = document.getElementById('stage');
  var slides = Array.prototype.slice.call(stage.querySelectorAll('.slide'));
  var progress = document.getElementById('progress');
  var counter = document.getElementById('counter');
  var notes = document.getElementById('notes');
  var N = slides.length;
  var cur = 0;
  var overview = false;
  var thumbs = [];

  slides.forEach(function (s, i) {
    var t = document.createElement('div');
    t.className = 'thumb';
    s.parentNode.insertBefore(t, s);
    t.appendChild(s);
    thumbs.push(t);
    var k = 0;
    Array.prototype.forEach.call(s.querySelectorAll('[data-a]'), function (e) {
      e.style.setProperty('--d', (0.12 + k * 0.08).toFixed(2) + 's');
      k++;
    });
  });

  function fromHash() {
    var n = parseInt((location.hash || '').replace('#', ''), 10);
    return isNaN(n) ? 0 : Math.min(Math.max(n - 1, 0), N - 1);
  }

  function fit() {
    if (overview) {
      var cols = window.innerWidth < 800 ? 2 : (window.innerWidth < 1300 ? 3 : 4);
      var pad = 40, gap = 24;
      var tw = (window.innerWidth - 2 * pad - (cols - 1) * gap - 17) / cols;
      stage.style.setProperty('--cols', cols);
      stage.style.setProperty('--tw', tw + 'px');
      stage.style.setProperty('--th', (tw * 9 / 16) + 'px');
      stage.style.setProperty('--ts', tw / W);
      stage.style.transform = '';
      return;
    }
    var s = Math.min(window.innerWidth / W, window.innerHeight / H);
    var x = (window.innerWidth - W * s) / 2;
    var y = (window.innerHeight - H * s) / 2;
    stage.style.transform = 'translate(' + x + 'px,' + y + 'px) scale(' + s + ')';
  }

  function go(n, silent) {
    n = Math.min(Math.max(n, 0), N - 1);
    cur = n;
    slides.forEach(function (s, i) {
      var on = i === n;
      s.classList.toggle('active', on);
      s.setAttribute('aria-hidden', on ? 'false' : 'true');
      thumbs[i].classList.toggle('cur', on);
    });
    progress.style.width = ((n + 1) / N * 100) + '%';
    counter.textContent = (n + 1) + ' / ' + N;
    var a = slides[n].querySelector('aside.notes');
    notes.textContent = '';
    var b = document.createElement('b');
    b.textContent = 'Notas (' + (n + 1) + '): ';
    notes.appendChild(b);
    notes.appendChild(document.createTextNode(a ? a.textContent.trim() : '—'));
    if (!silent && history.replaceState) history.replaceState(null, '', '#' + (n + 1));
    if (overview) thumbs[n].scrollIntoView({ block: 'nearest' });
  }

  function setOverview(on) {
    overview = on;
    document.body.classList.toggle('overview', on);
    fit();
    if (on) thumbs[cur].scrollIntoView({ block: 'center' });
  }

  function toggleFullscreen() {
    var d = document;
    if (d.fullscreenElement) { d.exitFullscreen(); }
    else if (d.documentElement.requestFullscreen) { d.documentElement.requestFullscreen(); }
  }

  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var k = e.key;
    if (k === 'ArrowRight' || k === 'ArrowDown' || k === 'PageDown' || k === ' ' || k === 'Enter') {
      e.preventDefault();
      if (overview && k === 'Enter') { setOverview(false); return; }
      go(cur + 1);
    } else if (k === 'ArrowLeft' || k === 'ArrowUp' || k === 'PageUp' || k === 'Backspace') {
      e.preventDefault(); go(cur - 1);
    } else if (k === 'Home') { go(0); }
    else if (k === 'End') { go(N - 1); }
    else if (k === 'f' || k === 'F') { toggleFullscreen(); }
    else if (k === 'o' || k === 'O') { setOverview(!overview); }
    else if (k === 'n' || k === 'N') { document.body.classList.toggle('show-notes'); }
    else if (k === 'Escape' && overview) { setOverview(false); }
  });

  stage.addEventListener('click', function (e) {
    if (overview) {
      var t = e.target;
      while (t && t !== stage && thumbs.indexOf(t) < 0) t = t.parentNode;
      var i = thumbs.indexOf(t);
      if (i >= 0) { go(i); setOverview(false); }
      return;
    }
    if (e.target.closest && e.target.closest('a,button')) return;
    if (e.clientX < window.innerWidth * 0.2) go(cur - 1); else go(cur + 1);
  });

  var sx = null, sy = null;
  document.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 1) return;
    sx = e.touches[0].clientX; sy = e.touches[0].clientY;
  }, { passive: true });
  document.addEventListener('touchend', function (e) {
    if (sx === null || overview) return;
    var t = e.changedTouches[0];
    var dx = t.clientX - sx, dy = t.clientY - sy;
    sx = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) { go(dx < 0 ? cur + 1 : cur - 1); }
  }, { passive: true });

  window.addEventListener('resize', fit);
  window.addEventListener('hashchange', function () { go(fromHash(), true); });

  fit();
  go(fromHash(), true);
})();
