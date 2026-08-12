/* facetmark site behaviour.
   No framework, no build step, no network calls. Everything here degrades to a
   readable static page if JavaScript is off.

   The terminal replay below is verbatim output from `facetmark demo --size 60`
   (mock provider, deterministic). Ranks, scores and titles are copied from the
   JSON the command prints; nothing is invented. Timings are from one recorded
   run and vary by machine. */

(function () {
  "use strict";

  var root = document.documentElement;
  var LS = (function () {
    try {
      var k = "__fm";
      localStorage.setItem(k, "1");
      localStorage.removeItem(k);
      return localStorage;
    } catch (e) {
      return null;
    }
  })();

  /* ---------- theme ------------------------------------------------------ */
  /* The pre-paint bootstrap lives inline in <head>; this only wires the
     toggle so a flash of the wrong theme is impossible. */

  function setTheme(t) {
    root.setAttribute("data-theme", t);
    if (LS) LS.setItem("fm-theme", t);
    var btns = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < btns.length; i++) {
      btns[i].textContent = t === "dark" ? "\u2600" : "\u263D";
      btns[i].setAttribute(
        "aria-label",
        t === "dark" ? "Switch to light theme" : "Switch to dark theme"
      );
    }
  }

  function initTheme() {
    setTheme(root.getAttribute("data-theme") === "dark" ? "dark" : "light");
    document.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest("[data-theme-toggle]");
      if (!b) return;
      e.preventDefault();
      setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });
  }

  /* ---------- language --------------------------------------------------- */
  /* Two files per page: `guide.html` and `guide.zh.html`. The switch is a real
     link (works without JS); JS only remembers the choice and, on a bare
     directory URL, follows the browser's own language preference once.
     The URL wins over the stored preference: a named file names its own
     language, so a shared `guide.html` opens in English even for a reader who
     once clicked 中文. Before this rule the stored preference bounced every
     explicit link and one of the two languages was simply unreachable. */

  function filename() {
    var p = location.pathname;
    return p.slice(p.lastIndexOf("/") + 1);
  }

  function counterpart() {
    var p = location.pathname;
    var cut = p.lastIndexOf("/") + 1;
    var base = p.slice(0, cut);
    var file = p.slice(cut) || "index.html";
    if (file.indexOf(".zh.html") > -1)
      return base + file.replace(".zh.html", ".html");
    if (file.indexOf(".html") > -1)
      return base + file.replace(".html", ".zh.html");
    return base + "index.zh.html";
  }

  function initLang() {
    var here = root.getAttribute("lang") === "zh-CN" ? "zh" : "en";
    var other = here === "zh" ? "en" : "zh";
    var target = counterpart();

    var links = document.querySelectorAll("[data-lang-switch]");
    for (var i = 0; i < links.length; i++) {
      links[i].setAttribute("href", target);
      links[i].addEventListener("click", function () {
        if (LS) LS.setItem("fm-lang", other);
      });
    }

    if (!LS) return;
    var saved = LS.getItem("fm-lang");
    /* Whatever the reader is actually reading becomes the remembered choice,
       so the next bare visit lands in the same language. */
    try {
      LS.setItem("fm-lang", here);
    } catch (e) {
      return;
    }
    /* A named file is an explicit request. Never redirect away from one. */
    if (filename() !== "") return;
    /* Only the bare directory URL carries no language. Follow the browser
       there, once, and only if the reader has never chosen. */
    if (saved) {
      if (saved !== here) location.replace(target);
      return;
    }
    if (sessionStorage.getItem("fm-auto")) return;
    try {
      sessionStorage.setItem("fm-auto", "1");
    } catch (e) {
      return;
    }
    var nav = (navigator.language || "").toLowerCase();
    var wants = nav.indexOf("zh") === 0 ? "zh" : "en";
    if (wants !== here) location.replace(target);
  }

  /* ---------- scroll progress -------------------------------------------- */

  function initProgress() {
    var bar = document.querySelector(".progress");
    if (!bar) return;
    var tick = false;
    function draw() {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + "%";
      tick = false;
    }
    addEventListener(
      "scroll",
      function () {
        if (!tick) {
          tick = true;
          requestAnimationFrame(draw);
        }
      },
      { passive: true }
    );
    draw();
  }

  /* ---------- reveal + bar animation ------------------------------------- */

  function initReveal() {
    var items = document.querySelectorAll(".reveal, .bars");
    if (!items.length) return;
    if (!("IntersectionObserver" in window)) {
      for (var i = 0; i < items.length; i++) {
        items[i].classList.add("in", "go");
      }
      return;
    }
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          en.target.classList.add(
            en.target.classList.contains("bars") ? "go" : "in"
          );
          io.unobserve(en.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    for (var j = 0; j < items.length; j++) io.observe(items[j]);
  }

  /* ---------- copy buttons ----------------------------------------------- */

  function initCopy() {
    document.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest("[data-copy]");
      if (!b) return;
      var block = b.closest(".cb");
      var code = block && block.querySelector("code");
      if (!code) return;
      var done = b.getAttribute("data-done") || "copied";
      var label = b.getAttribute("data-label") || "copy";
      var write =
        navigator.clipboard && navigator.clipboard.writeText
          ? navigator.clipboard.writeText(code.innerText)
          : Promise.reject();
      write.then(
        function () {
          b.textContent = done;
          setTimeout(function () {
            b.textContent = label;
          }, 1400);
        },
        function () {
          var r = document.createRange();
          r.selectNodeContents(code);
          var sel = getSelection();
          sel.removeAllRanges();
          sel.addRange(r);
        }
      );
    });
  }

  /* ---------- table of contents ------------------------------------------ */

  function initToc() {
    var links = document.querySelectorAll(".toc a[href^='#']");
    if (!links.length || !("IntersectionObserver" in window)) return;
    var map = {};
    var seen = [];
    for (var i = 0; i < links.length; i++) {
      var id = links[i].getAttribute("href").slice(1);
      var sec = document.getElementById(id);
      if (!sec) continue;
      map[id] = links[i];
      seen.push(sec);
    }
    var visible = {};
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (en) {
          visible[en.target.id] = en.isIntersecting;
        });
        var active = null;
        for (var k = 0; k < seen.length; k++) {
          if (visible[seen[k].id]) {
            active = seen[k].id;
            break;
          }
        }
        if (!active) return;
        for (var id2 in map) map[id2].classList.remove("on");
        map[active].classList.add("on");
      },
      { rootMargin: "-84px 0px -62% 0px", threshold: 0 }
    );
    for (var j = 0; j < seen.length; j++) io.observe(seen[j]);
  }

  /* ---------- terminal replay -------------------------------------------- */
  /* Verbatim from `facetmark demo --size 60 --json`, provider = mock.
     `rank` is the order the pipeline returned; `score` is the RRF fusion score,
     which stage E (the reranker) deliberately does not overwrite when it
     reorders. That is why the score column is not sorted. */

  var DEMO = [
    {
      q: "sqlite-vec latency shard recall",
      kind: "content",
      ms: "17.0",
      target: 2,
      hits: [
        ["Why chromadb changes the recall story", "0.0776"],
        ["sqlite-vec: notes on embedding", "0.0829"],
        ["hnswlib-5: notes on index", "0.0768"],
        ["qdrant-6: notes on persistence", "0.0767"],
        ["Evaluating pgvector-6 for filter", "0.0777"]
      ]
    },
    {
      q:
        "that thing I found when I wanted to keep vectors next to the rest of " +
        "my data without another server",
      kind: "vague",
      ms: "11.4",
      target: 5,
      hits: [
        ["Why pgvector changes the quantization story", "0.0675"],
        ["Evaluating hyde-6 for judgement", "0.0722"],
        ["bm25f-6: notes on candidate", "0.0693"],
        ["Evaluating monot5-6 for ablation", "0.0670"],
        ["sqlite-vec: notes on embedding", "0.0761"]
      ]
    },
    {
      q: "the other thing I saved around the same time as qdrant, the one about index",
      kind: "episodic",
      ms: "10.7",
      target: 0,
      hits: [
        ["hnswlib-5: notes on index", "0.0773"],
        ["sqlite-vec-6 in production, three months in", "0.0778"],
        ["Why vespa-5 changes the brute force story", "0.0770"],
        ["qdrant in production, three months in", "0.0749"],
        ["qdrant-6: notes on persistence", "0.0837"]
      ]
    }
  ];

  function initTerm() {
    var el = document.getElementById("term-body");
    if (!el) return;

    var L = {
      hits: el.getAttribute("data-t-hits") || "hits",
      found: el.getAttribute("data-t-found") || "target at rank",
      missed: el.getAttribute("data-t-missed") || "target not in top 5",
      kinds: {
        content: el.getAttribute("data-t-content") || "content-style query",
        vague: el.getAttribute("data-t-vague") || "vague query",
        episodic: el.getAttribute("data-t-episodic") || "episodic query"
      }
    };

    var reduced =
      matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

    function esc(s) {
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }

    function frame(d, typed, rows, tail) {
      var h = '<div><span class="pr">$</span> facetmark search <span class="q">"';
      h += esc(typed) + '"</span>';
      if (rows < 0) h += '<span class="caret"></span>';
      h += "</div>";
      h += '<div class="dim">// ' + esc(L.kinds[d.kind]) + "</div>";
      h += "<div>&nbsp;</div>";
      for (var i = 0; i < rows && i < d.hits.length; i++) {
        var tgt = i + 1 === d.target ? " tgt" : "";
        h +=
          '<div class="hit' +
          tgt +
          '"><span class="n">' +
          (i + 1) +
          '</span><span class="sc">' +
          d.hits[i][1] +
          '</span><span class="t">' +
          esc(d.hits[i][0]) +
          (tgt ? "  \u25c0" : "") +
          "</span></div>";
      }
      if (tail) {
        h += "<div>&nbsp;</div>";
        h +=
          '<div class="dim">' +
          d.hits.length +
          " " +
          esc(L.hits) +
          " \u00b7 " +
          d.ms +
          " ms \u00b7 " +
          (d.target
            ? esc(L.found) + " " + d.target
            : esc(L.missed)) +
          "</div>";
      }
      el.innerHTML = h;
    }

    if (reduced) {
      frame(DEMO[0], DEMO[0].q, DEMO[0].hits.length, true);
      return;
    }

    /* Reserve the height of the tallest frame so that rows appearing during
       replay never push the rest of the page around.  Measured here rather
       than hardcoded in CSS: the answer is 255px to 492px depending on
       viewport width and language, so any single number is a hole at some
       widths and a jump at others. */
    function fit() {
      var keep = el.innerHTML;
      var max = 0;
      el.style.minHeight = "0px";
      for (var i = 0; i < DEMO.length; i++) {
        frame(DEMO[i], DEMO[i].q, DEMO[i].hits.length, false);
        if (el.scrollHeight > max) max = el.scrollHeight;
        frame(DEMO[i], DEMO[i].q, DEMO[i].hits.length, true);
        if (el.scrollHeight > max) max = el.scrollHeight;
      }
      if (max) el.style.minHeight = Math.ceil(max) + "px";
      el.innerHTML = keep;
    }

    fit();
    var fitTimer = null;
    addEventListener("resize", function () {
      clearTimeout(fitTimer);
      fitTimer = setTimeout(fit, 150);
    });

    var qi = 0;
    var timer = null;
    var running = true;

    function wait(ms) {
      return new Promise(function (r) {
        timer = setTimeout(r, ms);
      });
    }

    function type(d) {
      return new Promise(function (done) {
        var i = 0;
        var step = d.q.length > 60 ? 14 : 30;
        (function next() {
          if (!running) return;
          frame(d, d.q.slice(0, i), -1, false);
          if (i >= d.q.length) {
            done();
            return;
          }
          i += d.q.length > 60 ? 2 : 1;
          if (i > d.q.length) i = d.q.length;
          timer = setTimeout(next, step);
        })();
      });
    }

    /* The first pass shows rather than types, and that is the whole point of
       it. `fit()` reserves the tallest frame's height -- 255px to 492px -- so
       a terminal that begins empty begins as half a screen of near-black with
       two lines at the top of it, in the hero, above the fold. It stayed that
       way for about 1.1s: 900ms to type the query, 240ms of pause, then five
       rows at 115ms each. Nobody waits through that to find out the panel has
       content; they read it as a broken picture, which is what it looked like
       in every screenshot taken of this page. So the first thing on screen is
       the finished frame -- byte-for-byte what the no-JS markup already shows
       -- and the replay starts one cycle in, on the second query, where it is
       an enhancement instead of a regression. */
    var first = true;

    async function loop() {
      while (running) {
        var d = DEMO[qi % DEMO.length];
        if (first) {
          first = false;
          frame(d, d.q, d.hits.length, true);
          await wait(3200);
          qi++;
          continue;
        }
        await type(d);
        await wait(240);
        for (var r = 1; r <= d.hits.length; r++) {
          if (!running) return;
          frame(d, d.q, r, false);
          await wait(115);
        }
        frame(d, d.q, d.hits.length, true);
        await wait(3200);
        qi++;
      }
    }

    /* Only animate while the terminal is actually on screen. */
    frame(DEMO[0], DEMO[0].q, DEMO[0].hits.length, true);
    if ("IntersectionObserver" in window) {
      var started = false;
      new IntersectionObserver(function (en) {
        if (en[0].isIntersecting && !started) {
          started = true;
          loop();
        }
      }).observe(el);
    } else {
      loop();
    }

    document.addEventListener("visibilitychange", function () {
      if (document.hidden) {
        running = false;
        clearTimeout(timer);
      } else if (!running) {
        running = true;
        loop();
      }
    });
  }

  /* ---------- go --------------------------------------------------------- */

  function boot() {
    initTheme();
    initLang();
    initProgress();
    initReveal();
    initCopy();
    initToc();
    initTerm();
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
