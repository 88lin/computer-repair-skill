/* ============================================================================
   Computer Repair Skill — site behaviour
   No framework, no network requests, no cookies. Data ships in playbooks.js
   as window.CRS_DATA so the page also works from file://.
   ========================================================================= */
(function () {
"use strict";

/* ---------------------------------------------------------------- helpers */
var $  = function (s, r) { return (r || document).querySelector(s); };
var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

var store = {
  get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
};

var reduceMotion = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

var DATA  = window.CRS_DATA || { total: 0, categories: [], platform_counts: {}, playbooks: [] };
var I18N  = window.CRS_I18N || { en: {}, ui: { zh: {}, en: {} } };
var LANG  = "zh";
var UI    = function () { return I18N.ui[LANG] || I18N.ui.zh || {}; };
var BLOB  = "https://github.com/88lin/computer-repair-skill/blob/main/skills/computer-repair-skill/references/";

/* ==========================================================================
   1 · Scroll reveal (P1) + scroll progress bar
   ======================================================================= */
function initReveal() {
  var nodes = $$(".rv");
  if (reduceMotion || !("IntersectionObserver" in window)) {
    nodes.forEach(function (n) { n.classList.add("is-in"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
  nodes.forEach(function (n) { io.observe(n); });
}

function initScrollbar() {
  var fill = $("#scrollbarFill");
  if (!fill) return;
  var raf = 0;
  function paint() {
    raf = 0;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var p = h > 0 ? Math.min(1, Math.max(0, window.pageYOffset / h)) : 0;
    fill.style.width = (p * 100).toFixed(2) + "%";
  }
  addEventListener("scroll", function () { if (!raf) raf = requestAnimationFrame(paint); }, { passive: true });
  addEventListener("resize", paint);
  paint();
}

/* Lenis smooths desktop wheel input; touch and reduced-motion contexts stay native. */
var smoothScroll = null;
function initSmoothScroll() {
  if (!window.Lenis || !window.matchMedia || !window.requestAnimationFrame) return;

  var desktop = matchMedia("(min-width: 768px) and (hover: hover) and (pointer: fine)");
  var motion = matchMedia("(prefers-reduced-motion: reduce)");
  var easeOutQuart = function (t) { return 1 - Math.pow(1 - t, 4); };
  var smoothFrame = 0;
  var wheelMotion = false;
  var clearWheelMotion = null;
  var wheelSettleDistance = 14;

  function destroy() {
    if (!smoothScroll) return;
    if (smoothFrame) cancelAnimationFrame(smoothFrame);
    smoothFrame = 0;
    if (clearWheelMotion) document.removeEventListener("click", clearWheelMotion, true);
    clearWheelMotion = null;
    wheelMotion = false;
    smoothScroll.destroy();
    smoothScroll = null;
    window.CRS_LENIS = null;
  }

  function create() {
    if (smoothScroll || !desktop.matches || motion.matches) return;
    smoothScroll = new window.Lenis({
      autoRaf: false,
      smoothWheel: true,
      syncTouch: false,
      lerp: 0.075,
      wheelMultiplier: 1.1,
      overscroll: false,
      /* Anchors use duration mode; CSS scroll-padding owns the fixed-nav offset. */
      anchors: {
        lerp: 0,
        duration: 1,
        easing: easeOutQuart
      },
      stopInertiaOnNavigate: true
    });

    smoothScroll.on("virtual-scroll", function (input) {
      if (input.event && input.event.type === "wheel") wheelMotion = true;
    });
    smoothScroll.on("scroll", function (lenis) {
      if (lenis.isScrolling === false) wheelMotion = false;
    });

    clearWheelMotion = function (ev) {
      if (ev.target.closest && ev.target.closest("a[href]")) wheelMotion = false;
    };
    document.addEventListener("click", clearWheelMotion, true);

    function raf(time) {
      if (!smoothScroll) return;
      var remaining = Math.abs(smoothScroll.targetScroll - smoothScroll.animatedScroll);
      if (wheelMotion && smoothScroll.isScrolling === "smooth"
          && remaining > 0 && remaining <= wheelSettleDistance) {
        /* Avoid a quantized 1px correction after several visually still frames. */
        smoothScroll.reset();
        wheelMotion = false;
      }
      smoothScroll.raf(time);
      smoothFrame = requestAnimationFrame(raf);
    }

    smoothFrame = requestAnimationFrame(raf);
    window.CRS_LENIS = smoothScroll;
    if (document.body.classList.contains("is-locked")) smoothScroll.stop();
  }

  function sync() {
    if (desktop.matches && !motion.matches) create();
    else destroy();
  }

  sync();
  if (desktop.addEventListener) desktop.addEventListener("change", sync);
  if (motion.addEventListener) motion.addEventListener("change", sync);
}

/* ==========================================================================
   2 · Nav active link + flow rail active step
   ======================================================================= */
function initSpy(linkSel, targets, onSet) {
  var links = $$(linkSel);
  if (!links.length) return;
  var secs = targets.map(function (id) { return document.getElementById(id); }).filter(Boolean);
  if (!secs.length) return;
  var raf = 0;
  function paint() {
    raf = 0;
    /* rect-based: ids may sit inside positioned ancestors, so offsetTop lies */
    var probe = window.innerHeight * 0.34;
    var cur = secs[0].id;
    for (var i = 0; i < secs.length; i++) {
      if (secs[i].getBoundingClientRect().top <= probe) cur = secs[i].id;
    }
    links.forEach(function (a) {
      var on = a.getAttribute("href") === "#" + cur;
      a.classList.toggle("is-on", on);
      if (on && onSet) onSet(a);
    });
  }
  addEventListener("scroll", function () { if (!raf) raf = requestAnimationFrame(paint); }, { passive: true });
  addEventListener("resize", paint);
  paint();
}

/* ==========================================================================
   3 · Hero typewriter — the page's single animation component
   ======================================================================= */
var typer = { timer: 0 };
function startTyper(force) {
  var el = $("#typeText");
  if (!el) return;
  var full = el.getAttribute("data-typewriter") || el.textContent;
  clearTimeout(typer.timer);
  if (reduceMotion) { el.textContent = full; return; }
  var line = $("#typeLine");
  var steps = $("#termSteps");
  if (steps) steps.classList.toggle("is-in", false);
  if (line) line.classList.remove("is-done");
  el.textContent = "";
  var chars = Array.from(full);
  var i = 0;
  function tick() {
    if (i >= chars.length) {
      if (line) line.classList.add("is-done");
      if (steps) steps.classList.add("is-in");
      return;
    }
    el.textContent += chars[i++];
    typer.timer = setTimeout(tick, 42 + Math.random() * 40);
  }
  typer.timer = setTimeout(tick, force ? 240 : 900);
}

function initTyper() {
  var el = $("#typeText");
  if (!el || reduceMotion) { return; }
  if (!("IntersectionObserver" in window)) { startTyper(true); return; }
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) { if (e.isIntersecting) { startTyper(false); io.unobserve(e.target); } });
  }, { threshold: 0.4 });
  io.observe(el);
}

/* ==========================================================================
   4 · Install tabs (WAI-ARIA tabs pattern)
   ======================================================================= */
function initTabs() {
  var root = $("#installTabs");
  if (!root) return;
  var tabs = $$(".tab", root);
  if (!tabs.length) return;

  function select(idx, focus) {
    tabs.forEach(function (t, i) {
      var on = i === idx;
      t.classList.toggle("is-on", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
      if (on) { t.removeAttribute("tabindex"); } else { t.setAttribute("tabindex", "-1"); }
      var p = document.getElementById(t.getAttribute("aria-controls"));
      if (p) { p.classList.toggle("is-hidden", !on); if (on) { p.removeAttribute("hidden"); } else { p.setAttribute("hidden", ""); } }
    });
    if (focus) tabs[idx].focus();
  }

  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { select(i, false); });
    t.addEventListener("keydown", function (ev) {
      var k = ev.key, n = -1;
      if (k === "ArrowRight" || k === "ArrowDown") n = (i + 1) % tabs.length;
      else if (k === "ArrowLeft" || k === "ArrowUp") n = (i - 1 + tabs.length) % tabs.length;
      else if (k === "Home") n = 0;
      else if (k === "End") n = tabs.length - 1;
      if (n >= 0) { ev.preventDefault(); select(n, true); }
    });
  });
  select(0, false);
}

/* ==========================================================================
   5 · Accordion (FAQ)
   ======================================================================= */
function initAcc() {
  var acc = $("#acc");
  if (!acc) return;
  $$(".acc-btn", acc).forEach(function (btn) {
    btn.addEventListener("click", function () {
      var item = btn.closest(".acc-item");
      var panel = document.getElementById(btn.getAttribute("aria-controls"));
      var open = item.classList.contains("is-open");
      if (open) {
        item.classList.remove("is-open");
        btn.setAttribute("aria-expanded", "false");
        if (panel) panel.setAttribute("hidden", "");
      } else {
        item.classList.add("is-open");
        btn.setAttribute("aria-expanded", "true");
        if (panel) panel.removeAttribute("hidden");
      }
    });
  });
}

/* ==========================================================================
   6 · Copy buttons + toast
   ======================================================================= */
var toastTimer = 0;
function toast(msg) {
  var t = $("#toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("is-on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(function () { t.classList.remove("is-on"); }, 1800);
}

function writeClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise(function (res, rej) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.cssText = "position:fixed;top:-1000px;opacity:0";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand && document.execCommand("copy");
      document.body.removeChild(ta);
      ok ? res() : rej(new Error("execCommand failed"));
    } catch (e) { rej(e); }
  });
}

function initCopy() {
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest ? ev.target.closest(".copybtn") : null;
    if (!btn) return;
    var text = btn.getAttribute("data-copy");
    if (!text) {
      var sel = btn.getAttribute("data-copy-from");
      var src = sel && $(sel);
      text = src ? src.textContent.replace(/\s+$/, "") : "";
    }
    if (!text) return;
    writeClipboard(text).then(function () {
      btn.classList.add("is-done");
      var lab = $("span", btn);
      var prev = lab ? lab.textContent : "";
      if (lab) lab.textContent = UI().copied;
      toast(UI().copied);
      setTimeout(function () {
        btn.classList.remove("is-done");
        if (lab) lab.textContent = prev;
      }, 1600);
    }).catch(function () { toast(UI().copyFail); });
  });
}

/* ==========================================================================
   7 · Prompt cards — slow, interruptible, seamless horizontal movement
   ======================================================================= */
var sayLoop = {
  root: null, track: null, loopWidth: 0, frame: 0, last: 0,
  paused: false, visible: false, active: false, observer: null
};

function cloneSayCards(track, originals) {
  originals.forEach(function (card) {
    var clone = card.cloneNode(true);
    clone.setAttribute("data-say-clone", "");
    clone.setAttribute("aria-hidden", "true");
    clone.setAttribute("inert", "");
    clone.removeAttribute("id");
    $$('[id]', clone).forEach(function (el) { el.removeAttribute("id"); });
    $$('button, a, input, select, textarea', clone).forEach(function (el) { el.setAttribute("tabindex", "-1"); });
    track.appendChild(clone);
  });
}

function refreshSayClones() {
  var track = sayLoop.track;
  if (!track || !sayLoop.active) return;

  $$(".say-card[data-say-clone]", track).forEach(function (card) { card.remove(); });
  var originals = $$(".say-card:not([data-say-clone])", track);
  if (!originals.length) return;
  cloneSayCards(track, originals);

  var first = originals[0];
  var firstClone = $(".say-card[data-say-clone]", track);
  sayLoop.loopWidth = first && firstClone ? firstClone.offsetLeft - first.offsetLeft : 0;

  /* Keep at least one viewport of cloned cards beyond the reset point. */
  var requiredWidth = sayLoop.loopWidth + (sayLoop.root ? sayLoop.root.clientWidth : 0) + 64;
  while (sayLoop.loopWidth && track.scrollWidth < requiredWidth) cloneSayCards(track, originals);

  if (sayLoop.root && sayLoop.loopWidth) {
    sayLoop.root.scrollLeft %= sayLoop.loopWidth;
  }
}

function normalizeSayScroll() {
  if (!sayLoop.active || !sayLoop.root || !sayLoop.loopWidth) return;
  if (sayLoop.root.scrollLeft >= sayLoop.loopWidth) {
    sayLoop.root.scrollLeft %= sayLoop.loopWidth;
  }
}

function stopSayLoop() {
  if (sayLoop.frame) cancelAnimationFrame(sayLoop.frame);
  sayLoop.frame = 0;
  sayLoop.last = 0;
  sayLoop.active = false;
  sayLoop.paused = false;
  sayLoop.loopWidth = 0;
  if (!sayLoop.root || !sayLoop.track) return;
  $$(".say-card[data-say-clone]", sayLoop.track).forEach(function (card) { card.remove(); });
  sayLoop.root.classList.remove("is-looping");
  sayLoop.track.classList.remove("is-looping");
  sayLoop.root.scrollLeft = 0;
}

function startSayLoop() {
  if (sayLoop.active || !sayLoop.root || !sayLoop.track) return;
  sayLoop.active = true;
  sayLoop.root.classList.add("is-looping");
  sayLoop.track.classList.add("is-looping");
  refreshSayClones();

  function move(now) {
    if (!sayLoop.active) return;
    if (!sayLoop.last) sayLoop.last = now;
    var elapsed = Math.min(64, now - sayLoop.last);
    sayLoop.last = now;
    if (!sayLoop.paused && sayLoop.visible && !document.hidden && sayLoop.loopWidth) {
      var next = (sayLoop.root.scrollLeft + elapsed * 0.036) % sayLoop.loopWidth;
      sayLoop.root.scrollLeft = next;
    }
    sayLoop.frame = requestAnimationFrame(move);
  }

  sayLoop.frame = requestAnimationFrame(move);
}

function initSayAutoScroll() {
  var root = $("#sayScroller");
  var track = root && $(".say-track", root);
  if (!root || !track || !window.matchMedia || !window.requestAnimationFrame) return;

  sayLoop.root = root;
  sayLoop.track = track;
  var desktop = matchMedia("(min-width: 768px) and (hover: hover) and (pointer: fine)");
  var motion = matchMedia("(prefers-reduced-motion: reduce)");

  if ("IntersectionObserver" in window) {
    sayLoop.observer = new IntersectionObserver(function (entries) {
      sayLoop.visible = entries.some(function (entry) { return entry.isIntersecting; });
      sayLoop.last = performance.now();
    }, { threshold: 0.08 });
    sayLoop.observer.observe(root);
  } else {
    sayLoop.visible = true;
  }

  function syncMode() {
    if (desktop.matches && !motion.matches) startSayLoop();
    else stopSayLoop();
  }

  addEventListener("resize", function () {
    if (sayLoop.active) requestAnimationFrame(refreshSayClones);
  });

  root.addEventListener("scroll", normalizeSayScroll, { passive: true });
  root.addEventListener("pointerenter", function () { if (sayLoop.active) sayLoop.paused = true; });
  root.addEventListener("pointerleave", function () {
    if (sayLoop.active) { sayLoop.paused = false; sayLoop.last = performance.now(); }
  });
  root.addEventListener("focusin", function () { if (sayLoop.active) sayLoop.paused = true; });
  root.addEventListener("focusout", function (ev) {
    if (sayLoop.active && !root.contains(ev.relatedTarget)) {
      sayLoop.paused = false;
      sayLoop.last = performance.now();
    }
  });
  root.addEventListener("pointerdown", function () { if (sayLoop.active) sayLoop.paused = true; });
  addEventListener("pointerup", function () {
    if (sayLoop.active) {
      sayLoop.paused = false;
      sayLoop.last = performance.now();
    }
  });

  syncMode();
  if (desktop.addEventListener) desktop.addEventListener("change", syncMode);
  if (motion.addEventListener) motion.addEventListener("change", syncMode);
}

/* ==========================================================================
   8 · Playbook index — stats, chips, table, search, modal
   ======================================================================= */
var PB = DATA.playbooks || [];
var CATS = DATA.categories || [];
var PLATS = ["all", "windows", "macos", "linux"];
var PLAT_LABEL = {
  all:     { zh: "跨平台", en: "Cross-platform" },
  windows: { zh: "Windows", en: "Windows" },
  macos:   { zh: "macOS",  en: "macOS" },
  linux:   { zh: "Linux",  en: "Linux" }
};
var PLAT_TAGCLASS = { all: "tagp-all", windows: "tagp-win", macos: "tagp-mac", linux: "tagp-lin" };

/* per-record search haystack, built once */
PB.forEach(function (p) {
  p._hay = [
    p.title_zh, p.title_en, p.detail_zh, p.detail_en, p.triggers_zh,
    p.prompt_zh, p.prompt_en, p.when_en, p.route, p.id,
    p.category_zh, p.category_en, p.platform_zh, p.platform_en, p.file
  ].join(" \u0001 ").toLowerCase();
});

var filter = { cat: "", plat: "", q: "" };

function catOf(slug) {
  for (var i = 0; i < CATS.length; i++) if (CATS[i].slug === slug) return CATS[i];
  return null;
}
function tx(p, zhKey, enKey) { return LANG === "en" ? (p[enKey] || p[zhKey]) : p[zhKey]; }

/* --- highlight: escape per slice so <mark> can never land inside an entity */
function hl(raw, tokens) {
  raw = String(raw == null ? "" : raw);
  if (!tokens || !tokens.length) return esc(raw);
  var low = raw.toLowerCase(), ranges = [];
  tokens.forEach(function (t) {
    if (!t) return;
    var from = 0, at;
    while ((at = low.indexOf(t, from)) !== -1) { ranges.push([at, at + t.length]); from = at + t.length; }
  });
  if (!ranges.length) return esc(raw);
  ranges.sort(function (a, b) { return a[0] - b[0]; });
  var merged = [ranges[0]];
  for (var i = 1; i < ranges.length; i++) {
    var last = merged[merged.length - 1];
    if (ranges[i][0] <= last[1]) { last[1] = Math.max(last[1], ranges[i][1]); }
    else merged.push(ranges[i]);
  }
  var out = "", cur = 0;
  merged.forEach(function (r) {
    out += esc(raw.slice(cur, r[0])) + "<mark>" + esc(raw.slice(r[0], r[1])) + "</mark>";
    cur = r[1];
  });
  return out + esc(raw.slice(cur));
}

/* --- category table + platform grid (static stats, no filtering) --------- */
function renderCatTable() {
  var body = $("#catTableBody");
  if (!body) return;
  var max = CATS.reduce(function (m, c) { return Math.max(m, c.count); }, 1);
  body.innerHTML = CATS.map(function (c) {
    var label = LANG === "en" ? (c.en || c.zh) : c.zh;
    return '<tr><td class="dots-e" aria-hidden="true">' + esc(c.emoji) + "</td>"
         + '<td class="dots-z">' + esc(label) + "</td>"
         + '<td class="dots-n">' + c.count + "</td>"
         + '<td class="dots-bar"><i style="width:' + Math.round(c.count / max * 100) + '%"></i></td></tr>';
  }).join("");
}

function renderPlatGrid() {
  var grid = $("#platGrid");
  if (!grid) return;
  var pc = DATA.platform_counts || {};
  grid.innerHTML = PLATS.map(function (k) {
    return "<li><b class=\"plat-n\">" + (pc[k] || 0) + "</b>"
         + '<span class="plat-t">' + esc(PLAT_LABEL[k][LANG] || PLAT_LABEL[k].zh) + "</span></li>";
  }).join("");
}

/* --- filter chips ------------------------------------------------------- */
function renderChips() {
  var box = $("#pbChips");
  if (!box) return;
  var u = UI(), html = "";
  html += chip("cat", "", u.all, DATA.total, filter.cat === "", u.catAria);
  CATS.forEach(function (c) {
    var label = (c.emoji ? c.emoji + " " : "") + (LANG === "en" ? (c.en || c.zh) : c.zh);
    html += chip("cat", c.slug, label, c.count, filter.cat === c.slug, u.catAria);
  });
  html += '<span class="chip-sep" aria-hidden="true"></span>';
  var pc = DATA.platform_counts || {};
  PLATS.forEach(function (k) {
    html += chip("plat", k, PLAT_LABEL[k][LANG] || PLAT_LABEL[k].zh, pc[k] || 0, filter.plat === k, u.platAria);
  });
  if (filter.cat || filter.plat || filter.q) {
    html += '<button type="button" class="chip chip-clear" data-clear="1">' + esc(u.clear) + "</button>";
  }
  box.innerHTML = html;
}

function chip(kind, val, label, count, on, aria) {
  return '<button type="button" class="chip' + (on ? " is-on" : "")
       + '" data-' + kind + '="' + esc(val) + '" aria-pressed="' + (on ? "true" : "false")
       + '" aria-label="' + esc(String(aria || "") + String(label)) + '">'
       + "<span>" + esc(label) + '</span><span class="chip-n">' + count + "</span></button>";
}

/* --- the 58-row index table -------------------------------------------- */
function tokens() {
  return filter.q.toLowerCase().split(/\s+/).filter(function (t) { return t.length > 0; });
}

function matches(p, tk) {
  if (filter.cat && p.category_slug !== filter.cat) return false;
  if (filter.plat && p.platform !== filter.plat) return false;
  for (var i = 0; i < tk.length; i++) if (p._hay.indexOf(tk[i]) === -1) return false;
  return true;
}

function rowHtml(p, n, tk) {
  var title = tx(p, "title_zh", "title_en");
  var detail = tx(p, "detail_zh", "detail_en");
  var cat = LANG === "en" ? (p.category_en || p.category_zh) : p.category_zh;
  var plat = LANG === "en" ? (p.platform_en || p.platform_zh) : p.platform_zh;
  return '<tr class="pb-row" data-id="' + esc(p.id) + '">'
       + '<td class="pb-i">' + (n < 10 ? "0" + n : n) + "</td>"
       + '<td class="pb-t"><span class="pb-t-e" aria-hidden="true">' + esc(p.emoji) + "</span>"
       + '<button type="button" class="pb-open" aria-label="' + esc(UI().rowAria + title) + '">'
       + hl(title, tk) + "</button>"
       + '<span class="pb-t-d">' + hl(detail, tk) + "</span></td>"
       + '<td class="pb-c">' + esc(cat) + "</td>"
       + '<td class="pb-p"><span class="tagp ' + PLAT_TAGCLASS[p.platform] + '">' + esc(plat) + "</span></td>"
       + '<td class="pb-r">' + hl(p.route, tk) + "</td></tr>";
}

function renderTable() {
  var body = $("#pbBody");
  if (!body) return;
  var tk = tokens(), rows = [], n = 0;
  PB.forEach(function (p) {
    if (!matches(p, tk)) return;
    rows.push(rowHtml(p, ++n, tk));
  });
  body.innerHTML = rows.join("");
  var count = $("#pbCount");
  if (count) count.textContent = (UI().count || "{n}/{t}").replace("{n}", n).replace("{t}", DATA.total);
  var empty = $("#pbEmpty");
  if (empty) empty.classList.toggle("is-hidden", n > 0);
  var wrap = $(".pb-tablewrap");
  if (wrap) wrap.style.display = n > 0 ? "" : "none";
}

/* --- modal -------------------------------------------------------------- */
var modalState = { last: null };

function dl(dt, dd, quote) {
  if (!dd) return "";
  return "<dt>" + esc(dt) + "</dt><dd" + (quote ? ' class="is-quote"' : "") + ">" + esc(dd) + "</dd>";
}

function openModal(id) {
  var modal = $("#modal");
  var p = null;
  for (var i = 0; i < PB.length; i++) if (PB[i].id === id) { p = PB[i]; break; }
  if (!modal || !p) return;
  var u = UI();
  var cat = LANG === "en" ? (p.category_en || p.category_zh) : p.category_zh;
  $("#modalKicker").textContent = (p.emoji ? p.emoji + "  " : "") + cat;
  $("#modalTitle").textContent = tx(p, "title_zh", "title_en");
  $("#modalDetail").textContent = tx(p, "detail_zh", "detail_en");
  var when = LANG === "en" ? (p.when_en || p.triggers_zh) : p.triggers_zh;
  $("#modalDl").innerHTML =
      dl(LANG === "en" ? u.mWhen : u.mTriggers, when, false)
    + dl(u.mPrompt, tx(p, "prompt_zh", "prompt_en"), true)
    + dl(u.mPlatform, LANG === "en" ? (p.platform_en || p.platform_zh) : p.platform_zh, false)
    + dl(u.mReviewed, p.last_reviewed, false)
    + dl(u.mFile, p.file, false);
  var src = $("#modalSrc");
  if (src) src.setAttribute("href", BLOB + p.file);

  modalState.last = document.activeElement;
  modal.removeAttribute("hidden");
  document.body.classList.add("is-locked");
  if (smoothScroll) smoothScroll.stop();
  var x = $(".modal-x", modal);
  if (x) x.focus();
}

function closeModal() {
  var modal = $("#modal");
  if (!modal || modal.hasAttribute("hidden")) return;
  modal.setAttribute("hidden", "");
  document.body.classList.remove("is-locked");
  if (smoothScroll) smoothScroll.start();
  if (modalState.last && modalState.last.focus) modalState.last.focus();
  modalState.last = null;
}

function initModal() {
  var modal = $("#modal");
  if (!modal) return;
  modal.addEventListener("click", function (ev) {
    if (ev.target.closest("[data-modal-close]") || ev.target.closest(".modal-x")) closeModal();
  });
  document.addEventListener("keydown", function (ev) {
    if (modal.hasAttribute("hidden")) return;
    if (ev.key === "Escape") { ev.preventDefault(); closeModal(); return; }
    if (ev.key !== "Tab") return;
    var f = $$('a[href],button:not([disabled]),[tabindex]:not([tabindex="-1"])', modal)
      .filter(function (n) { return n.offsetParent !== null; });
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
    else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
  });
}

/* --- wire the playbook section ----------------------------------------- */
var searchTimer = 0;
function initPlaybooks() {
  renderCatTable();
  renderPlatGrid();
  renderChips();
  renderTable();

  var chips = $("#pbChips");
  if (chips) chips.addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b) return;
    if (b.hasAttribute("data-clear")) {
      filter.cat = ""; filter.plat = ""; filter.q = "";
      var inp = $("#pbSearch"); if (inp) inp.value = "";
    } else if (b.hasAttribute("data-cat")) {
      var c = b.getAttribute("data-cat");
      filter.cat = (filter.cat === c) ? "" : c;
    } else if (b.hasAttribute("data-plat")) {
      var pl = b.getAttribute("data-plat");
      filter.plat = (filter.plat === pl) ? "" : pl;
    } else return;
    renderChips(); renderTable();
  });

  var input = $("#pbSearch");
  if (input) input.addEventListener("input", function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () {
      filter.q = input.value.trim();
      renderChips(); renderTable();
    }, 110);
  });

  var body = $("#pbBody");
  if (body) body.addEventListener("click", function (ev) {
    var tr = ev.target.closest(".pb-row");
    if (tr) openModal(tr.getAttribute("data-id"));
  });
  initModal();
}

/* ==========================================================================
   9 · Language toggle
   ======================================================================= */
var snap = null;
var booted = false;

function i18nNodes() { return $$("[data-i18n], [data-i18n-html]"); }

function snapshotZh() {
  snap = i18nNodes().map(function (el) { return [el, el.innerHTML]; });
  $$("[data-i18n-attr]").forEach(function (el) {
    el.getAttribute("data-i18n-attr").split(",").forEach(function (part) {
      var bits = part.split("|");
      if (bits.length !== 2) return;
      var a = bits[0].trim();
      el.setAttribute("data-i18n-zh-" + a.replace(/[^a-z0-9-]/gi, ""), el.getAttribute(a) || "");
    });
  });
}

function applyLang(lang) {
  var en = lang === "en";
  var dict = I18N.en || {};
  LANG = en ? "en" : "zh";

  if (snap) {
    snap.forEach(function (pair) {
      var el = pair[0];
      if (!en) { el.innerHTML = pair[1]; return; }
      var key = el.getAttribute("data-i18n") || el.getAttribute("data-i18n-html");
      if (key && dict[key] != null) el.innerHTML = dict[key];
    });
  }
  $$("[data-i18n-attr]").forEach(function (el) {
    el.getAttribute("data-i18n-attr").split(",").forEach(function (part) {
      var bits = part.split("|");
      if (bits.length !== 2) return;
      var a = bits[0].trim(), key = bits[1].trim();
      if (en) { if (dict[key] != null) el.setAttribute(a, dict[key]); }
      else {
        var zh = el.getAttribute("data-i18n-zh-" + a.replace(/[^a-z0-9-]/gi, ""));
        if (zh != null) el.setAttribute(a, zh);
      }
    });
  });

  document.documentElement.setAttribute("lang", en ? "en" : "zh-CN");
  var btn = $("#langBtn");
  if (btn) { btn.classList.toggle("is-en", en); }
  store.set("crs-lang", LANG);

  /* re-render everything JS produced, then restart the one animation */
  renderCatTable(); renderPlatGrid(); renderChips(); renderTable();
  refreshSayClones();
  if (booted) startTyper(true);
}

function initLang() {
  snapshotZh();
  var q = null;
  try { q = new URLSearchParams(location.search).get("lang"); } catch (e) {}
  var want = q || store.get("crs-lang");
  if (!want) want = /^zh\b/i.test(navigator.language || "") ? "zh" : "en";
  if (want === "en") applyLang("en");

  var btn = $("#langBtn");
  if (btn) btn.addEventListener("click", function () { applyLang(LANG === "en" ? "zh" : "en"); });
}

/* ==========================================================================
   boot
   ======================================================================= */
function boot() {
  initLang();          /* snapshot before anything mutates the DOM copy */
  initPlaybooks();
  initReveal();
  initScrollbar();
  initSmoothScroll();
  initTabs();
  initAcc();
  initCopy();
  initSayAutoScroll();
  initTyper();
  initSpy(".nav-links a", ["what", "flow", "safety", "install", "playbooks", "prompts", "faq"]);
  initSpy(".flow-rail .frl", ["step1", "step2", "step3", "step4", "step5", "step6", "step7"]);
  booted = true;
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();

})();
