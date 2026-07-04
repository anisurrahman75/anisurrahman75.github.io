// Table of contents + reading position for blog posts.
// Builds a fixed right-hand "Contents" panel from the article's h2 headings,
// highlights the section currently being read, and draws a thin reading
// progress bar along the top. Injected outside the app root, so it works
// with the client-side-rendered pages. No dependencies.
(function () {
  "use strict";

  function slugify(text) {
    return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "section";
  }

  function accent() {
    var root = document.querySelector("[style*='--accent']");
    if (root) {
      var m = /--accent\s*:\s*([^;"]+)/.exec(root.getAttribute("style") || "");
      if (m) return m[1].trim();
    }
    return "#46c8c0";
  }

  function init() {
    var article = document.querySelector("article");
    if (!article) return false;
    var headings = Array.prototype.slice.call(article.querySelectorAll("h2"));
    if (headings.length < 2) return false;           // no catalogue for single-section posts
    if (document.getElementById("toc-panel")) return true;

    var ac = accent();

    // --- ids on headings, offset for the sticky header
    var seen = {};
    headings.forEach(function (h) {
      if (!h.id) {
        var id = slugify(h.textContent);
        while (seen[id] || document.getElementById(id)) id += "-2";
        seen[id] = true;
        h.id = id;
      }
      h.style.scrollMarginTop = "92px";
    });

    // --- styles
    var style = document.createElement("style");
    style.textContent =
      "#toc-progress{position:fixed;top:0;left:0;height:3px;width:0;z-index:200;background:" + ac + ";transition:width .1s linear;}" +
      "#toc-panel{position:fixed;top:120px;left:calc(50% + 392px);width:212px;z-index:60;font-family:'IBM Plex Mono',ui-monospace,monospace;}" +
      "#toc-panel .toc-title{font-size:10.5px;letter-spacing:0.16em;text-transform:uppercase;opacity:0.55;margin:0 0 10px;}" +
      "#toc-panel ol{list-style:none;margin:0;padding:0;border-left:1px solid rgba(128,140,155,0.25);}" +
      "#toc-panel a{display:block;font-size:12.5px;line-height:1.45;padding:5px 0 5px 14px;margin-left:-1px;color:inherit;opacity:0.55;text-decoration:none;border-left:2px solid transparent;transition:opacity .15s,border-color .15s;}" +
      "#toc-panel a:hover{opacity:0.9;}" +
      "#toc-panel a.toc-active{opacity:1;border-left-color:" + ac + ";color:" + ac + ";}" +
      "@media (max-width:1279px){#toc-panel{display:none;}}";
    document.body.appendChild(style);

    // --- progress bar
    var bar = document.createElement("div");
    bar.id = "toc-progress";
    document.body.appendChild(bar);

    // --- panel
    var panel = document.createElement("nav");
    panel.id = "toc-panel";
    panel.setAttribute("aria-label", "Table of contents");
    var title = document.createElement("p");
    title.className = "toc-title";
    title.textContent = "Contents";
    panel.appendChild(title);
    var list = document.createElement("ol");
    var links = headings.map(function (h) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#" + h.id;
      a.textContent = h.textContent;
      li.appendChild(a);
      list.appendChild(li);
      return a;
    });
    panel.appendChild(list);
    document.body.appendChild(panel);

    // --- reading position
    function update() {
      var doc = document.documentElement;
      var max = doc.scrollHeight - window.innerHeight;
      bar.style.width = (max > 0 ? Math.min(100, (window.scrollY / max) * 100) : 0) + "%";

      var current = -1;
      for (var i = 0; i < headings.length; i++) {
        if (headings[i].getBoundingClientRect().top <= 140) current = i;
        else break;
      }
      links.forEach(function (a, i) {
        a.classList.toggle("toc-active", i === current);
      });
    }
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
    return true;
  }

  // The page body is rendered client-side; poll briefly until the article exists.
  var tries = 0;
  var timer = setInterval(function () {
    if (init() || ++tries > 120) clearInterval(timer);
  }, 100);
})();
