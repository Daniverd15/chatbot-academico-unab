/* UNABot web client — vanilla JS, sin dependencias. */
(function () {
  'use strict';

  var MOCK = /(^|[?&])mock=1(&|$)/.test(location.search);
  var TIMEOUT_MS = 75000;
  var SS_KEY = 'unabot-session';

  var $ = function (id) { return document.getElementById(id); };
  var state = { codigo: '', pin: '', session: '', busy: false, dash: null, gen: 0 };
  var inflight = [];
  function newSession() { state.gen++; inflight.splice(0).forEach(function (c) { try { c.abort(); } catch (e) {} }); }

  /* ---------- utilidades ---------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function num(v, d) { var n = Number(v); return isFinite(n) && v !== null && v !== '' ? n : (d === undefined ? null : d); }
  function fmt(v, dec) { var n = num(v); return n === null ? '—' : n.toLocaleString('es-CO', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec == null ? 2 : dec }); }
  function money(v) { var n = num(v); return n === null ? '—' : n.toLocaleString('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }); }
  function pretty(s) { s = String(s == null ? '' : s).replace(/_/g, ' ').trim().toLowerCase(); return s ? s.charAt(0).toUpperCase() + s.slice(1) : '—'; }
  function fdate(s) {
    if (!s) return '';
    var d = new Date(String(s).length <= 10 ? s + 'T00:00:00' : s);
    return isNaN(d) ? String(s) : d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
  }
  function safeUrl(u) { return /^https?:\/\//i.test(String(u || '').trim()) ? String(u).trim() : null; }
  function store(k, v) { try { if (v == null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
  function toast(msg) {
    var t = $('toast'); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(function () { t.hidden = true; }, 3200);
  }
  function uuid() {
    try { if (crypto.randomUUID) return crypto.randomUUID(); } catch (e) {}
    return 'web-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  /* ---------- tema ---------- */
  $('themeBtn').addEventListener('click', function () {
    var root = document.documentElement;
    var cur = root.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var next = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('unabot-theme', next); } catch (e) {}
  });

  /* ---------- Markdown seguro: se construyen nodos DOM, nunca HTML en cadena ---------- */
  var INLINE_RE = /`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)|(https?:\/\/[^\s<>]*[^\s<>).,;:!?])|\*\*([^*]+?)\*\*|__([^_]+?)__|\*([^*\s][^*]*?)\*|_([^_\s][^_]*?)_/g;
  function linkNode(url, label) {
    var u = null;
    try { var p = new URL(String(url).trim()); if (p.protocol === 'http:' || p.protocol === 'https:') u = p.href; } catch (e) {}
    if (!u) return null;
    var a = document.createElement('a');
    a.setAttribute('href', u); a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer');
    if (label != null) a.textContent = label;
    return a;
  }
  function inlineInto(parent, t, noLink) {
    t = String(t == null ? '' : t);
    var re = new RegExp(INLINE_RE.source, 'g'), last = 0, m;
    function text(s) { if (s) parent.appendChild(document.createTextNode(s)); }
    while ((m = re.exec(t))) {
      var prev = m.index > 0 ? t.charAt(m.index - 1) : '', next = t.charAt(re.lastIndex);
      var node = null;
      if (m[1] != null) { node = el('code', null, m[1]); }
      else if (m[2] != null) {
        if (!noLink) { node = linkNode(m[3]); if (node) inlineInto(node, m[2], true); }
        if (!node) { text(t.slice(last, m.index)); inlineInto(parent, m[2], noLink); last = re.lastIndex; continue; }
      } else if (m[4] != null) {
        if (!noLink && (prev === '' || /[\s(]/.test(prev))) node = linkNode(m[4], m[4]);
      } else if (m[5] != null || m[6] != null) {
        node = document.createElement('strong'); inlineInto(node, m[5] != null ? m[5] : m[6], noLink);
      } else if (m[7] != null) {
        if (!/[*\w]/.test(prev) && !/\w/.test(next)) { node = document.createElement('em'); inlineInto(node, m[7], noLink); }
      } else if (m[8] != null) {
        if (!/[_\w]/.test(prev) && !/\w/.test(next)) { node = document.createElement('em'); inlineInto(node, m[8], noLink); }
      }
      text(t.slice(last, m.index));
      if (node) parent.appendChild(node); else text(m[0]);
      last = re.lastIndex;
    }
    text(t.slice(last));
    return parent;
  }
  function inl(tag, t) { return inlineInto(document.createElement(tag), t); }
  function renderMd(src) {
    var lines = String(src == null ? '' : src).replace(/\r\n?/g, '\n').split('\n');
    var out = document.createDocumentFragment(), i = 0, m;
    function isTableSep(l) { return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(l || ''); }
    function cells(l) { return l.trim().replace(/^\||\|$/g, '').split('|').map(function (c) { return c.trim(); }); }
    while (i < lines.length) {
      var line = lines[i];
      if (/^\s*$/.test(line)) { i++; continue; }
      if ((m = /^\s*```/.exec(line))) {
        var buf = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) buf.push(lines[i++]);
        i++; var pre = document.createElement('pre'); pre.appendChild(el('code', null, buf.join('\n'))); out.appendChild(pre); continue;
      }
      if ((m = /^(#{1,6})\s+(.+)$/.exec(line))) {
        out.appendChild(inl('h' + Math.min(5, Math.max(3, m[1].length + 2)), m[2])); i++; continue;
      }
      if (/^\s*([-*_])(\s*\1){2,}\s*$/.test(line)) { out.appendChild(document.createElement('hr')); i++; continue; }
      if (line.indexOf('|') > -1 && isTableSep(lines[i + 1])) {
        var head = cells(line); i += 2; var rows = [];
        while (i < lines.length && lines[i].indexOf('|') > -1 && !/^\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
        var tb = document.createElement('table'), th = tb.appendChild(document.createElement('thead')).appendChild(document.createElement('tr'));
        head.forEach(function (c) { th.appendChild(inl('th', c)); });
        var tbody = tb.appendChild(document.createElement('tbody'));
        rows.forEach(function (r) { var tr = tbody.appendChild(document.createElement('tr')); r.forEach(function (c) { tr.appendChild(inl('td', c)); }); });
        out.appendChild(tb); continue;
      }
      if (/^\s*>/.test(line)) {
        var q = [];
        while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ''));
        out.appendChild(inl('blockquote', q.join(' '))); continue;
      }
      if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+[.)]\s+/.test(line)) {
        var ord = /^\s*\d+[.)]\s+/.test(line), list = document.createElement(ord ? 'ol' : 'ul');
        var re = ord ? /^\s*\d+[.)]\s+(.*)$/ : /^\s*[-*+]\s+(.*)$/;
        while (i < lines.length && (m = re.exec(lines[i]))) {
          var it = m[1]; i++;
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !re.test(lines[i])) it += ' ' + lines[i++].trim();
          list.appendChild(inl('li', it));
        }
        out.appendChild(list); continue;
      }
      var p = [];
      while (i < lines.length && !/^\s*$/.test(lines[i]) && !/^(#{1,6}\s|\s*>|\s*```|\s*[-*+]\s+|\s*\d+[.)]\s+)/.test(lines[i])) p.push(lines[i++]);
      if (!p.length) { p.push(lines[i++]); }
      var pe = document.createElement('p');
      p.forEach(function (l, k) { if (k) pe.appendChild(document.createElement('br')); inlineInto(pe, l); });
      out.appendChild(pe);
    }
    return out;
  }

  /* Autoprueba: ?mock=1&selftest=1 renderiza cargas hostiles y verifica el DOM resultante. */
  function selfTest() {
    var payloads = [
      '[x](https://a/(https://b/onmouseover=location=origin//)',
      '[x](https://a/" onmouseover="alert(1))',
      '[x](javascript:alert(1))', '[x](JaVaScRiPt:alert(1))', '[x](data:text/html,<script>alert(1)</script>)',
      '[<img src=x onerror=alert(1)>](https://ok.com)', '<img src=x onerror=alert(1)>', '<script>alert(1)</script>',
      'https://a.com/" onmouseover="alert(1)', 'https://a.com/<img src=x onerror=alert(1)>',
      '(https://a.com/x onmouseover=alert(1))', '**[a](https://b.com/" onfocus="x)**', '`[x](javascript:alert(1))`',
      '| a | b |\n|---|---|\n| [x](javascript:1) | <b onclick=1> |', '> [x](vbscript:1) "onload="1', '- [x](https://a/ onclick=1)',
      '[[x](https://a.com)](https://b.com)', '# <svg onload=alert(1)>', '```\n<a href="javascript:1" onclick="1">\n```'
    ];
    var box = document.createElement('div'); box.id = 'selftest'; box.hidden = true; document.body.appendChild(box);
    var bad = 0;
    payloads.forEach(function (pl) {
      var d = document.createElement('div'); d.appendChild(renderMd(pl)); box.appendChild(d);
      Array.prototype.forEach.call(d.querySelectorAll('*'), function (n) {
        Array.prototype.forEach.call(n.attributes, function (a) {
          var ok = !/^on/i.test(a.name);
          if (!ok) bad++;
          console.assert(ok, 'selftest: atributo de evento en <' + n.tagName + '>: ' + a.name, pl);
        });
        if (n.tagName === 'A') {
          var ok2 = /^https?:\/\//i.test(n.getAttribute('href') || '') && n.getAttribute('target') === '_blank' && /noopener/.test(n.getAttribute('rel') || '');
          if (!ok2) bad++;
          console.assert(ok2, 'selftest: <a> con href inválido: ' + n.getAttribute('href'), pl);
        }
        if (/^(SCRIPT|IMG|SVG|IFRAME)$/i.test(n.tagName)) { bad++; console.assert(false, 'selftest: elemento inesperado ' + n.tagName, pl); }
      });
    });
    console.log('selftest markdown: ' + payloads.length + ' cargas, ' + bad + ' fallos');
    window.__selftestFailures = bad;
  }

  /* ---------- API ---------- */
  function api(path, body) {
    if (MOCK) return mockApi(path, body);
    var ctrl = new AbortController(), timedOut = false;
    inflight.push(ctrl);
    var timer = setTimeout(function () { timedOut = true; ctrl.abort(); }, TIMEOUT_MS);
    return fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: ctrl.signal })
      .then(function (r) {
        return r.text().then(function (t) {
          var j = null; try { j = t ? JSON.parse(t) : null; } catch (e) {}
          if (!r.ok && !j) { var err = new Error('http'); err.status = r.status; throw err; }
          return j || {};
        });
      })
      .catch(function (e) {
        if (e && e.name === 'AbortError') { var t = new Error(timedOut ? 'timeout' : 'aborted'); t.kind = timedOut ? 'timeout' : 'aborted'; throw t; }
        throw e;
      })
      .finally(function () { clearTimeout(timer); var k = inflight.indexOf(ctrl); if (k > -1) inflight.splice(k, 1); });
  }
  function friendly(e) {
    if (e && e.kind === 'timeout') return 'La respuesta tardó demasiado (más de 75 s). Intenta de nuevo en un momento.';
    if (e && e.status === 401) return 'Código o PIN incorrectos.';
    if (e && e.status === 429) return 'Demasiadas solicitudes seguidas. Espera unos segundos e inténtalo otra vez.';
    if (e && e.status >= 500) return 'El servidor tuvo un problema. Inténtalo de nuevo en unos minutos.';
    return 'No pude conectarme con el servidor. Revisa tu conexión e inténtalo de nuevo.';
  }

  /* ---------- login ---------- */
  var demoChips = document.querySelectorAll('.demo');
  Array.prototype.forEach.call(demoChips, function (b) {
    b.addEventListener('click', function () {
      $('codigo').value = b.getAttribute('data-code'); $('pin').value = '1234';
      Array.prototype.forEach.call(demoChips, function (x) { x.classList.toggle('on', x === b); });
      $('loginErr').hidden = true; $('pin').focus();
    });
  });
  $('loginForm').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var codigo = $('codigo').value.trim().toUpperCase(), pin = $('pin').value.trim();
    var err = $('loginErr');
    if (!codigo || !pin) { err.textContent = 'Ingresa tu código y tu PIN.'; err.hidden = false; return; }
    err.hidden = true;
    var btn = $('loginBtn'); btn.classList.add('loading'); btn.disabled = true;
    var gen = state.gen;
    api('/api/app/login', { codigo: codigo, pin: pin }).then(function (r) {
      if (gen !== state.gen) return;
      if (r && r.ok) { enter(codigo, pin, r.estudiante || {}); }
      else { err.textContent = (r && r.mensaje) || 'Código o PIN incorrectos.'; err.hidden = false; }
    }).catch(function (e) { if (gen !== state.gen) return; err.textContent = friendly(e); err.hidden = false; })
      .then(function () { btn.classList.remove('loading'); btn.disabled = false; });
  });

  function enter(codigo, pin, est) {
    newSession(); state.busy = false; $('sendBtn').disabled = false;
    state.codigo = codigo; state.pin = pin; state.session = state.session || uuid();
    store(SS_KEY, JSON.stringify({ codigo: codigo, pin: pin, session: state.session, nombre: est.nombre_completo || '' }));
    $('loginView').hidden = true; $('appView').hidden = false;
    var first = String(est.nombre_completo || '').split(' ')[0];
    $('welcome').textContent = first ? 'Hola, ' + first : 'Hola';
    $('log').textContent = '';
    addBot('¡Hola' + (first ? ', **' + first + '**' : '') + '! Soy **UNABot**. Puedo ayudarte con tu avance, tu proyección de grado, tus cursos y el calendario. ¿Qué quieres saber?', {});
    renderSuggestions();
    loadDashboard();
    $('appView').scrollIntoView({ behavior: 'smooth', block: 'start' });
    setTimeout(function () { $('msg').focus({ preventScroll: true }); }, 400);
  }
  function logout() {
    newSession(); state.busy = false; $('sendBtn').disabled = false; typing(false); $('log').textContent = '';
    store(SS_KEY, null); state.codigo = state.pin = ''; state.session = ''; state.dash = null;
    $('appView').hidden = true; $('loginView').hidden = false; $('pin').value = '';
    $('panelBody').textContent = '';
    document.getElementById('probar').scrollIntoView({ behavior: 'smooth' });
  }
  $('logoutBtn').addEventListener('click', logout);

  /* ---------- tabs móviles ---------- */
  Array.prototype.forEach.call(document.querySelectorAll('.mtabs button'), function (b) {
    b.addEventListener('click', function () {
      var v = b.getAttribute('data-view');
      document.querySelector('.shell').setAttribute('data-view', v);
      Array.prototype.forEach.call(document.querySelectorAll('.mtabs button'), function (x) { x.setAttribute('aria-selected', String(x === b)); });
    });
  });

  /* ---------- panel del estudiante ---------- */
  function loadDashboard() {
    var pb = $('panelBody'); pb.textContent = '';
    var sk = el('div', 'card pcard', 'Cargando tu panel…'); sk.style.color = 'var(--muted)'; pb.appendChild(sk);
    var gen = state.gen;
    api('/api/app/dashboard', { codigo: state.codigo, pin: state.pin }).then(function (d) {
      if (gen !== state.gen) return;
      if (!d || !d.ok) throw new Error('bad');
      state.dash = d; renderPanel(d);
    }).catch(function (e) {
      if (gen !== state.gen) return;
      pb.textContent = '';
      var c = el('div', 'card pcard'); c.appendChild(el('p', 'empty', 'No pude cargar tu panel. ' + friendly(e)));
      var b = el('button', 'btn btn-ghost btn-sm', 'Reintentar'); b.type = 'button'; b.style.marginTop = '10px'; b.addEventListener('click', loadDashboard);
      c.appendChild(b); pb.appendChild(c);
    });
  }
  function card(title) { var c = el('section', 'card pcard'); if (title) c.appendChild(el('h3', null, title)); return c; }
  function tag(text, cls) { return el('span', 'tag ' + (cls || ''), text); }
  function estadoClass(s) {
    s = String(s || '').toLowerCase();
    if (/prueba|riesgo|suspend|bloque|pendiente|mora/.test(s)) return /pendiente|mora/.test(s) ? 'warn' : 'bad';
    if (/normal|activ|al d[ií]a|excel|bueno|vigente|matricul/.test(s)) return 'ok';
    return 'info';
  }
  function renderPanel(d) {
    var r = d.resumen || {}, pb = $('panelBody'); pb.textContent = '';
    var nombre = r.nombre_completo || 'Estudiante';

    // Identidad + progreso
    var c1 = card();
    var id = el('div', 'ident');
    id.appendChild(el('div', 'avatar', nombre.trim().split(/\s+/).slice(0, 2).map(function (w) { return w.charAt(0); }).join('').toUpperCase()));
    var idt = el('div'); idt.appendChild(el('strong', null, nombre));
    idt.appendChild(el('small', null, 'Código ' + state.codigo)); id.appendChild(idt); c1.appendChild(id);

    var pct = Math.max(0, Math.min(100, num(r.porcentaje_avance, 0)));
    var R = 52, C = 2 * Math.PI * R;
    var prog = el('div', 'prog'); prog.style.marginTop = '16px';
    var ringBox = el('div');
    ringBox.innerHTML = '<svg class="ring" viewBox="0 0 120 120" role="img" aria-label="Avance de la carrera: ' + esc(fmt(pct, 0)) + ' por ciento">' +
      '<defs><linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8E00E6"/><stop offset="1" stop-color="#F7A600"/></linearGradient></defs>' +
      '<circle class="trk" cx="60" cy="60" r="' + R + '" fill="none" stroke-width="11"/>' +
      '<circle class="bar" cx="60" cy="60" r="' + R + '" fill="none" stroke-width="11" stroke-linecap="round" transform="rotate(-90 60 60)" stroke-dasharray="' + C.toFixed(2) + '" stroke-dashoffset="' + C.toFixed(2) + '"/>' +
      '<text x="60" y="64" text-anchor="middle" font-size="24" font-weight="700">' + esc(fmt(pct, 0)) + '%</text>' +
      '<text x="60" y="82" text-anchor="middle" font-size="9" style="fill:var(--muted)">avance</text></svg>';
    prog.appendChild(ringBox.firstChild);
    var st = el('div', 'stats');
    [['Créditos', fmt(r.creditos_aprobados, 0) + ' / ' + fmt(r.creditos_totales, 0)],
     ['Semestre', r.semestre_por_creditos != null ? fmt(r.semestre_por_creditos, 0) : '—'],
     ['Matrícula', pretty(r.estado_matricula_actual)],
     ['Saldo', money(r.saldo_pendiente)]].forEach(function (p) {
      var row = el('div'); row.appendChild(el('span', null, p[0])); row.appendChild(el('b', null, p[1])); st.appendChild(row);
    });
    prog.appendChild(st); c1.appendChild(prog);
    requestAnimationFrame(function () { requestAnimationFrame(function () {
      var bar = c1.querySelector('.bar'); if (bar) bar.setAttribute('stroke-dashoffset', (C * (1 - pct / 100)).toFixed(2));
    }); });

    var pr = el('div', 'pga-row');
    var pn = el('div', 'pga-n'); pn.appendChild(el('small', null, 'PGA acumulado')); pn.appendChild(document.createTextNode(r.pga_acumulado != null ? fmt(r.pga_acumulado, 2) : '—'));
    pr.appendChild(pn);
    var tg = el('div', 'tags');
    if (r.estado_academico) tg.appendChild(tag(pretty(r.estado_academico), estadoClass(r.estado_academico)));
    if (d.riesgo && d.riesgo.nivel) {
      var nv = String(d.riesgo.nivel).toLowerCase(), pc = num(d.riesgo.probabilidad);
      tg.appendChild(tag('Riesgo ' + nv + (pc !== null ? ' · ' + fmt(pc <= 1 ? pc * 100 : pc, 0) + '%' : ''), /alto/.test(nv) ? 'bad' : /medio|moder/.test(nv) ? 'warn' : 'ok'));
    }
    pr.appendChild(tg); c1.appendChild(pr); pb.appendChild(c1);

    // Alertas
    var al = (d.alertas || []);
    if (al.length) {
      var c2 = card('Alertas'); var ul = el('ul', 'alerts');
      al.forEach(function (a) {
        var p = String(a.prioridad || 'INFO').toUpperCase(); if (['ALTA', 'MEDIA', 'BAJA', 'INFO'].indexOf(p) < 0) p = 'INFO';
        var li = el('li', 'alert ' + p); li.appendChild(el('span', 'pr', p)); li.appendChild(el('span', null, a.mensaje || pretty(a.tipo))); ul.appendChild(li);
      }); c2.appendChild(ul); pb.appendChild(c2);
    }

    // Competencias
    var cp = d.competencias || [];
    if (cp.length) {
      var c3 = card('Competencias digitales'); var ol = el('ol', 'steps');
      cp.forEach(function (x, idx) {
        var li = el('li', 'step ' + (x.cumplida ? 'done' : x.en_curso ? 'cur' : ''));
        li.appendChild(el('span', 'node', x.cumplida ? '✓' : String(idx + 1)));
        var bx = el('div'); bx.appendChild(el('b', null, x.ruta_nombre || x.ruta || 'Ruta'));
        bx.appendChild(el('small', null, (x.cumplida ? 'Cumplida' : x.en_curso ? 'En curso' : 'Pendiente') + (x.detalle ? ' · ' + x.detalle : '')));
        li.appendChild(bx); ol.appendChild(li);
      }); c3.appendChild(ol); pb.appendChild(c3);
    }

    // Proyección
    var py = d.proyeccion;
    if (py) {
      var c4 = card('Proyección de grado'); var kv = el('div', 'kv'); var pp = py.proyeccion_probabilistica || {};
      [['Semestres restantes', py.semestres_restantes_ideal != null ? fmt(py.semestres_restantes_ideal, 0) : null],
       ['Grado ideal', py.periodo_grado_ideal],
       ['Más probable (P50)', pp.periodo_grado_p50],
       ['Escenario cauteloso (P90)', pp.periodo_grado_p90]].forEach(function (p) {
        if (p[1] == null || p[1] === '') return;
        var row = el('div'); row.appendChild(el('span', null, p[0])); row.appendChild(el('b', null, String(p[1]))); kv.appendChild(row);
      });
      if (kv.children.length) { c4.appendChild(kv); pb.appendChild(c4); }
    }

    // Historial PGA
    var hs = (d.historial_pga || []).filter(function (h) { return num(h.pga_periodo) !== null; });
    if (hs.length) { var c5 = card('Evolución del PGA'); var ch = el('div', 'chart'); ch.innerHTML = lineChart(hs); c5.appendChild(ch); pb.appendChild(c5); }

    // Calendario / noticias
    var cal = (d.calendario || []).slice(0, 4);
    if (cal.length) {
      var c6 = card('Próximas fechas'); var k2 = el('div', 'kv');
      cal.forEach(function (e) { var row = el('div'); row.appendChild(el('span', null, e.evento || pretty(e.categoria))); row.appendChild(el('b', null, fdate(e.fecha_inicio))); k2.appendChild(row); });
      c6.appendChild(k2); pb.appendChild(c6);
    }
    var nw = (d.noticias || []).slice(0, 3);
    if (nw.length) {
      var c7 = card('Noticias y convocatorias'); var nl = el('ul', 'news');
      nw.forEach(function (n) {
        var li = el('li'), u = safeUrl(n.url), t = n.titulo || 'Sin título';
        if (u) { var a = el('a', null, t); a.href = u; a.target = '_blank'; a.rel = 'noopener noreferrer'; li.appendChild(a); } else li.appendChild(el('b', null, t));
        li.appendChild(el('small', null, [pretty(n.tipo), fdate(n.fecha_pub)].filter(function (x) { return x && x !== '—'; }).join(' · ')));
        nl.appendChild(li);
      }); c7.appendChild(nl); pb.appendChild(c7);
    }
  }

  function lineChart(h) {
    var W = 340, H = 170, L = 30, Rr = 12, T = 12, B = 30;
    var vals = h.map(function (x) { return num(x.pga_periodo); });
    var lo = Math.min.apply(null, vals.concat([2.8])), hi = Math.max.apply(null, vals.concat([3.4]));
    lo = Math.floor(lo * 5) / 5; hi = Math.ceil(hi * 5) / 5; if (hi > 5) hi = 5;
    var iw = W - L - Rr, ih = H - T - B;
    function X(i) { return L + (h.length === 1 ? iw / 2 : i * iw / (h.length - 1)); }
    function Y(v) { return T + ih - (v - lo) / (hi - lo) * ih; }
    var s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Gráfico del PGA por periodo"><defs><linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8E00E6" stop-opacity=".25"/><stop offset="1" stop-color="#8E00E6" stop-opacity="0"/></linearGradient></defs>';
    [[3.0, 'var(--bad)'], [3.2, 'var(--warn)']].forEach(function (rf) {
      if (rf[0] < lo || rf[0] > hi) return;
      s += '<line class="ref" x1="' + L + '" x2="' + (W - Rr) + '" y1="' + Y(rf[0]).toFixed(1) + '" y2="' + Y(rf[0]).toFixed(1) + '" stroke="' + rf[1] + '"/>' +
        '<text x="' + (L - 4) + '" y="' + (Y(rf[0]) + 3.5).toFixed(1) + '" text-anchor="end">' + rf[0].toFixed(1) + '</text>';
    });
    var pts = h.map(function (x, i) { return X(i).toFixed(1) + ',' + Y(vals[i]).toFixed(1); });
    if (h.length > 1) s += '<path class="area" d="M' + pts.join(' L') + ' L' + X(h.length - 1).toFixed(1) + ',' + (T + ih) + ' L' + X(0).toFixed(1) + ',' + (T + ih) + 'Z"/>';
    s += '<polyline class="ln" points="' + pts.join(' ') + '"/>';
    var step = Math.ceil(h.length / 6);
    h.forEach(function (x, i) {
      s += '<circle class="pt" cx="' + X(i).toFixed(1) + '" cy="' + Y(vals[i]).toFixed(1) + '" r="3.6"><title>' + esc(x.periodo_id) + ': ' + esc(fmt(vals[i], 2)) + '</title></circle>';
      if (i % step === 0 || i === h.length - 1) s += '<text x="' + X(i).toFixed(1) + '" y="' + (H - 10) + '" text-anchor="middle">' + esc(String(x.periodo_id || '').slice(-6)) + '</text>';
    });
    return s + '</svg>';
  }

  /* ---------- chat ---------- */
  var SUGGESTIONS = ['¿Cómo voy en la carrera?', '¿Cuándo me gradúo?', '¿Qué cursos puedo inscribir?', '¿Qué es la insignia de competencias digitales?', '¿Cuándo son las inscripciones vacacionales?', '¿Qué cursos de competencias digitales he tomado?', 'Noticias y convocatorias'];
  function renderSuggestions() {
    var box = $('suggest'); box.textContent = '';
    SUGGESTIONS.forEach(function (q) {
      var b = el('button', 'chip', q); b.type = 'button';
      b.addEventListener('click', function () { sendMsg(q); }); box.appendChild(b);
    });
  }
  function scrollDown() { var l = $('log'); l.scrollTop = l.scrollHeight; }
  function addUser(text) {
    var m = el('div', 'msg user'); m.appendChild(el('div', 'bubble', text)); $('log').appendChild(m); scrollDown();
  }
  function addBot(md, o) {
    o = o || {};
    var m = el('div', 'msg bot' + (o.bloqueado ? ' blocked' : '') + (o.error ? ' error' : ''));
    var b = el('div', 'bubble md'); b.appendChild(renderMd(md)); m.appendChild(b);
    var meta = el('div', 'meta'), has = false;
    if (o.intencion) { meta.appendChild(el('span', 'pill', pretty(o.intencion))); has = true; }
    (o.fuentes || []).forEach(function (f) {
      if (!f) return; var u = safeUrl(f.url), t = f.titulo || f.url || 'Fuente';
      var s = u ? el('a', 'src', t) : el('span', 'src', t);
      if (u) { s.href = u; s.target = '_blank'; s.rel = 'noopener noreferrer'; } s.title = t; meta.appendChild(s); has = true;
    });
    if (o.log_id != null && !o.error) {
      var fb = el('div', 'fb'); fb.setAttribute('role', 'group'); fb.setAttribute('aria-label', 'Calificar respuesta');
      [['👍', 5, 'Respuesta útil'], ['👎', 1, 'Respuesta no útil']].forEach(function (x) {
        var bt = el('button', null, x[0]); bt.type = 'button'; bt.setAttribute('aria-label', x[2]); bt.title = x[2];
        bt.addEventListener('click', function () {
          Array.prototype.forEach.call(fb.children, function (k) { k.disabled = true; }); bt.classList.add('sel');
          var gen = state.gen;
          api('/api/app/feedback', { codigo: state.codigo, pin: state.pin, log_id: o.log_id, calificacion: x[1] })
            .then(function (r) { if (gen !== state.gen) return; toast(r && r.ok === false ? 'No se pudo registrar tu calificación.' : '¡Gracias por tu opinión!'); })
            .catch(function () { if (gen !== state.gen) return; toast('No se pudo registrar tu calificación.'); });
        }); fb.appendChild(bt);
      }); meta.appendChild(fb); has = true;
    }
    if (has) m.appendChild(meta);
    $('log').appendChild(m); scrollDown();
  }
  function typing(on) {
    var t = $('typingRow');
    if (on && !t) {
      t = el('div', 'msg bot typing'); t.id = 'typingRow'; t.setAttribute('aria-label', 'UNABot está escribiendo');
      var b = el('div', 'bubble'); b.appendChild(el('i')); b.appendChild(el('i')); b.appendChild(el('i')); t.appendChild(b);
      $('log').appendChild(t); scrollDown();
    } else if (!on && t) t.remove();
  }
  function sendMsg(text) {
    text = String(text || '').trim();
    if (!text || state.busy) return;
    state.busy = true; $('sendBtn').disabled = true;
    addUser(text); typing(true);
    $('msg').value = ''; autosize();
    var gen = state.gen;
    api('/api/chat', { codigo: state.codigo, pin: state.pin, mensaje: text, session_id: state.session }).then(function (r) {
      if (gen !== state.gen) return;
      typing(false); r = r || {};
      var txt = r.respuesta || (r.bloqueado ? 'No puedo ayudarte con esa solicitud.' : 'No recibí una respuesta. ¿Puedes reformular tu pregunta?');
      addBot(txt, { intencion: r.intencion, fuentes: r.fuentes, bloqueado: r.bloqueado, log_id: r.log_id });
    }).catch(function (e) { if (gen !== state.gen) return; typing(false); addBot(friendly(e), { error: true }); })
      .then(function () { if (gen !== state.gen) return; state.busy = false; $('sendBtn').disabled = false; $('msg').focus({ preventScroll: true }); });
  }
  function autosize() { var t = $('msg'); t.style.height = 'auto'; t.style.height = Math.min(140, t.scrollHeight) + 'px'; }
  $('msg').addEventListener('input', autosize);
  $('msg').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendMsg(this.value); }
  });
  $('chatForm').addEventListener('submit', function (e) { e.preventDefault(); sendMsg($('msg').value); });

  /* ---------- mock (?mock=1) ---------- */
  var MOCK_USERS = {
    U00100001: { n: 'Valentina Rojas Mejía', av: 78, cr: 112, pga: 4.31, ea: 'NORMAL', em: 'MATRICULADO', saldo: 0, sem: 8, h: [4.1, 4.2, 4.4, 4.3, 4.5, 4.2, 4.4], r: ['BAJO', 0.06] },
    U00100002: { n: 'Andrés Camilo Pérez Suárez', av: 41, cr: 59, pga: 2.78, ea: 'PRUEBA_ACADEMICA', em: 'MATRICULADO', saldo: 0, sem: 5, h: [3.4, 3.1, 2.9, 2.6, 2.8, 2.7], r: ['ALTO', 0.71] },
    U00100003: { n: 'Laura Sofía Gómez Ortiz', av: 96, cr: 138, pga: 3.82, ea: 'NORMAL', em: 'MATRICULADO', saldo: 0, sem: 10, h: [3.6, 3.7, 3.9, 3.8, 3.9, 3.8, 3.7, 4.0], r: ['BAJO', 0.03] },
    U00100004: { n: 'Juan David Torres Niño', av: 4, cr: 6, pga: null, ea: 'NORMAL', em: 'MATRICULADO', saldo: 0, sem: 1, h: [], r: null },
    U00100005: { n: 'Mariana Castillo Duarte', av: 55, cr: 79, pga: 3.45, ea: 'NORMAL', em: 'PAGO_PENDIENTE', saldo: 3850000, sem: 6, h: [3.3, 3.5, 3.4, 3.6, 3.4], r: ['MEDIO', 0.28] }
  };
  function mockApi(path, body) {
    return new Promise(function (res, rej) {
      setTimeout(function () {
        var u = MOCK_USERS[body && body.codigo];
        if (path === '/api/app/login') {
          if (u && body.pin === '1234') res({ ok: true, estudiante: { codigo: body.codigo, nombre_completo: u.n, programa: 'Ingeniería de Sistemas', cohorte: '2022-1' } });
          else res({ ok: false, mensaje: 'Código o PIN incorrectos. Prueba con una cuenta de demostración.' });
        } else if (path === '/api/app/dashboard') {
          if (!u) return res({ ok: false });
          var low = u.ea !== 'NORMAL';
          res({ ok: true, resumen: { nombre_completo: u.n, porcentaje_avance: u.av, creditos_aprobados: u.cr, creditos_totales: 144, pga_acumulado: u.pga, estado_academico: u.ea, estado_matricula_actual: u.em, saldo_pendiente: u.saldo, semestre_por_creditos: u.sem },
            alertas: low ? [{ prioridad: 'ALTA', tipo: 'PRUEBA', mensaje: 'Estás en prueba académica: necesitas subir tu PGA por encima de 3.0.' }, { prioridad: 'MEDIA', tipo: 'TUTORIA', mensaje: 'Agenda una tutoría con tu director de programa.' }]
              : u.saldo ? [{ prioridad: 'MEDIA', tipo: 'PAGO', mensaje: 'Tienes un saldo pendiente que puede bloquear tu inscripción.' }, { prioridad: 'INFO', tipo: 'CAL', mensaje: 'Las inscripciones vacacionales abren pronto.' }]
              : [{ prioridad: 'INFO', tipo: 'CAL', mensaje: 'Las inscripciones vacacionales abren pronto.' }, { prioridad: 'BAJA', tipo: 'OK', mensaje: 'Vas al día con tu plan de estudios.' }],
            competencias: [{ ruta: 'R1', ruta_nombre: 'Pensamiento computacional', cumplida: u.av > 30, en_curso: false, detalle: 'Fundamentos' }, { ruta: 'R2', ruta_nombre: 'Analítica de datos', cumplida: u.av > 70, en_curso: u.av > 40 && u.av <= 70, detalle: '2 de 3 cursos' }, { ruta: 'R3', ruta_nombre: 'Inteligencia artificial aplicada', cumplida: u.av > 90, en_curso: u.av > 70 && u.av <= 90, detalle: '' }],
            proyeccion: u.av > 5 ? { semestres_restantes_ideal: Math.max(1, Math.round((100 - u.av) / 11)), periodo_grado_ideal: u.av > 90 ? '2027-1' : '2028-1', proyeccion_probabilistica: { periodo_grado_p50: u.av > 90 ? '2027-1' : '2028-2', periodo_grado_p90: u.av > 90 ? '2027-2' : '2029-1' } } : null,
            riesgo: u.r ? { nivel: u.r[0], probabilidad: u.r[1] } : null,
            historial_pga: u.h.map(function (v, i) { return { periodo_id: (2022 + Math.floor((i + 1) / 2)) + '-' + (((i + 1) % 2) + 1), pga_periodo: v, estado_academico: u.ea }; }),
            noticias: [{ titulo: 'Convocatoria de monitorías 2027-1', url: 'https://www.unab.edu.co/', fecha_pub: '2026-11-05', tipo: 'CONVOCATORIA', resumen: '' }, { titulo: 'Semana de la Ingeniería', url: 'https://www.unab.edu.co/', fecha_pub: '2026-10-28', tipo: 'NOTICIA', resumen: '' }],
            calendario: [{ categoria: 'INSCRIPCIONES', evento: 'Inscripciones vacacionales', fecha_inicio: '2026-11-24', fecha_fin: '2026-12-05' }, { categoria: 'ACADEMICO', evento: 'Fin de clases', fecha_inicio: '2026-11-28', fecha_fin: null }, { categoria: 'EXAMENES', evento: 'Exámenes finales', fecha_inicio: '2026-12-01', fecha_fin: '2026-12-12' }] });
        } else if (path === '/api/chat') {
          var q = String(body.mensaje || '').toLowerCase();
          var out = { respuesta: 'Puedo ayudarte con tu avance, proyección de grado, cursos y calendario. ¿Sobre qué quieres saber?', intencion: 'general', fuentes: [], bloqueado: false, log_id: 100 + Math.floor(Math.random() * 900) };
          if (/ignora|prompt|contraseña|hackea/.test(q)) { out.respuesta = 'No puedo ayudarte con esa solicitud. Estoy aquí para apoyarte con temas académicos de la UNAB.'; out.bloqueado = true; out.intencion = 'bloqueado'; out.log_id = null; }
          else if (/voy|carrera|avance/.test(q)) { out.intencion = 'historia_academica'; out.respuesta = '### Tu avance\n\n' + (u ? 'Llevas **' + u.av + '%** de la carrera (' + u.cr + ' de 144 créditos) con un PGA de **' + (u.pga != null ? u.pga.toFixed(2) : 'N/D') + '**.' : 'Aún no tengo tus datos.') + '\n\n- Estado académico: `' + (u ? u.ea : '—') + '`\n- Sigue así y revisa tus alertas en el panel.\n\n> Recuerda que el PGA mínimo para mantenerte es **3.0**.'; }
          else if (/gradú|grado/.test(q)) { out.intencion = 'proyeccion_grado'; out.respuesta = 'Según la **simulación Monte Carlo**:\n\n| Escenario | Periodo |\n|---|---|\n| Ideal | 2028-1 |\n| P50 (más probable) | 2028-2 |\n| P90 (cauteloso) | 2029-1 |\n\nPuedes acelerar tomando cursos en vacaciones.'; }
          else if (/inscrib|cursos puedo/.test(q)) { out.intencion = 'oferta_cursos'; out.respuesta = 'Con tus prerrequisitos cumplidos puedes inscribir:\n\n1. **Bases de Datos II** (3 créditos)\n2. **Ingeniería de Software II** (3 créditos)\n3. *Electiva de profundización* (2 créditos)\n\nRevisa el reglamento: [Reglamento estudiantil](https://www.unab.edu.co/).'; out.fuentes = [{ titulo: 'Reglamento estudiantil', url: 'https://www.unab.edu.co/' }]; }
          else if (/insignia|competencias digitales/.test(q) && !/he tomado/.test(q)) { out.intencion = 'rag_reglamento'; out.respuesta = 'La **insignia de competencias digitales** certifica que completaste una ruta de formación digital: *pensamiento computacional*, *analítica* o *IA aplicada*.'; out.fuentes = [{ titulo: 'Insignias UNAB', url: 'https://www.unab.edu.co/' }, { titulo: 'Guía de competencias', url: '' }]; }
          else if (/vacacional/.test(q)) { out.intencion = 'calendario'; out.respuesta = 'Las **inscripciones vacacionales** son del **24 de noviembre al 5 de diciembre de 2026**.'; out.fuentes = [{ titulo: 'Calendario académico', url: 'https://www.unab.edu.co/' }]; }
          else if (/he tomado/.test(q)) { out.intencion = 'competencias'; out.respuesta = 'Hasta ahora has cursado:\n\n- Introducción a la programación\n- Analítica de datos I\n\nTe falta *un curso* para completar la ruta de analítica.'; }
          else if (/noticias|convocatoria/.test(q)) { out.intencion = 'noticias'; out.respuesta = '### Novedades\n\n- **Convocatoria de monitorías 2027-1** (5 nov)\n- **Semana de la Ingeniería** (28 oct)'; out.fuentes = [{ titulo: 'Noticias UNAB', url: 'https://www.unab.edu.co/' }]; }
          res(out);
        } else if (path === '/api/app/feedback') res({ ok: true });
        else rej(new Error('404'));
      }, path === '/api/chat' ? 900 : 350);
    });
  }

  /* ---------- init ---------- */
  if (MOCK) $('mockFlag').hidden = false;
  if (MOCK && /(^|[?&])selftest=1(&|$)/.test(location.search)) selfTest();
  var saved = load(SS_KEY);
  if (saved) {
    try {
      var s = JSON.parse(saved);
      if (s && s.codigo && s.pin) {
        state.session = s.session || '';
        enter(s.codigo, s.pin, { nombre_completo: s.nombre || '' });
        // evita saltar de scroll al restaurar la sesión
        window.scrollTo(0, 0);
      }
    } catch (e) { store(SS_KEY, null); }
  }
})();
