// Mount the crochetsim demo models and keep them in step with the documentation
// theme's light/dark toggle.
//
// Loaded after plotly.min.js and figures.js, both of which sit beside this file.
// Figure data lives in window.crochetsim.figures; window.crochetsim.themes holds
// one small colour overlay per scheme, so switching scheme only restyles the
// layout - the traces, which are the expensive part, are never rebuilt.
(function () {
  "use strict";

  var store = window.crochetsim || { figures: {}, themes: {} };
  var systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)");
  var mounted = [];

  function scheme() {
    var declared =
      (document.body && document.body.getAttribute("data-md-color-scheme")) ||
      document.documentElement.getAttribute("data-md-color-scheme");
    if (declared) return declared === "slate" ? "dark" : "light";
    return systemPrefersDark.matches ? "dark" : "light";
  }

  // The overlay is nested (font, legend, scene.xaxis...), so merge rather than
  // replace; anything that is not a plain object (arrays, colours) overwrites.
  function merge(base, extra) {
    var merged = {};
    var key;
    for (key in base) {
      if (Object.prototype.hasOwnProperty.call(base, key)) merged[key] = base[key];
    }
    for (key in extra) {
      if (!Object.prototype.hasOwnProperty.call(extra, key)) continue;
      var before = base[key];
      var after = extra[key];
      if (
        before && after && typeof before === "object" && typeof after === "object" &&
        !Array.isArray(before) && !Array.isArray(after)
      ) {
        merged[key] = merge(before, after);
      } else {
        merged[key] = after;
      }
    }
    return merged;
  }

  function layoutFor(element) {
    var figure = store.figures[element.getAttribute("data-viz")];
    if (!figure) return null;
    return merge(figure.layout, store.themes[scheme()] || {});
  }

  function draw(element) {
    if (element.getAttribute("data-drawn")) return;
    var figure = store.figures[element.getAttribute("data-viz")];
    var layout = layoutFor(element);
    if (!figure || !layout) return;
    if (!window.Plotly) {
      element.setAttribute("data-drawn", "failed");
      element.innerHTML =
        '<p class="crochetsim-fallback">plotly.js could not be initialised.</p>';
      return;
    }
    element.setAttribute("data-drawn", "1");
    window.Plotly.newPlot(element, figure.data, layout, {
      responsive: true,
      scrollZoom: true,
      displaylogo: false,
      toImageButtonOptions: {
        format: "png",
        scale: 2,
        filename: "crochetsim-" + element.getAttribute("data-viz"),
      },
    });
  }

  function restyle() {
    mounted.forEach(function (element) {
      if (element.getAttribute("data-drawn") !== "1" || !window.Plotly) return;
      window.Plotly.react(
        element,
        store.figures[element.getAttribute("data-viz")].data,
        layoutFor(element)
      );
    });
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        if (!entry.target.getAttribute("data-drawn")) mounted.push(entry.target);
        draw(entry.target);
      });
    },
    { rootMargin: "300px 0px" }
  );

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-viz]"), function (element) {
      observer.observe(element);
    });
  }

  if (document.body) {
    new MutationObserver(restyle).observe(document.body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"],
    });
  }
  systemPrefersDark.addEventListener("change", restyle);
  // Material's instant navigation re-renders the page body without a reload, so
  // re-observe on every navigation if that global is present.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(init);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
