(function () {
  const BURST_INTERVAL_MS = 120_000;
  const BURST_DURATION_MS = 3_000;
  const INITIAL_DELAY_MS = 5_000;
  const SHUTTLE_COUNT = 20;
  const SHUTTLE = "\u{1F3F8}";

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function randomBetween(min, max) {
    return min + Math.random() * (max - min);
  }

  function createContainer() {
    const el = document.createElement("div");
    el.id = "shuttle-rain";
    el.className = "shuttle-rain";
    el.setAttribute("aria-hidden", "true");
    document.body.appendChild(el);
    return el;
  }

  function runBurst(container) {
    const fragment = document.createDocumentFragment();
    for (let i = 0; i < SHUTTLE_COUNT; i += 1) {
      const item = document.createElement("span");
      item.className = "shuttle-rain__item";
      item.textContent = SHUTTLE;
      const duration = randomBetween(2.2, 3.2);
      const delay = randomBetween(0, 0.8);
      const size = randomBetween(1.1, 1.75);
      item.style.left = randomBetween(0, 92) + "%";
      item.style.fontSize = size + "rem";
      item.style.animationDuration = duration + "s";
      item.style.animationDelay = delay + "s";
      item.style.setProperty("--shuttle-spin", randomBetween(-180, 180) + "deg");
      fragment.appendChild(item);
    }
    container.appendChild(fragment);
    window.setTimeout(function () {
      container.replaceChildren();
    }, BURST_DURATION_MS);
  }

  function maybeBurst(container) {
    if (document.visibilityState === "hidden") {
      return;
    }
    runBurst(container);
  }

  function init() {
    if (prefersReducedMotion()) {
      return;
    }
    const container = createContainer();
    window.setTimeout(function () {
      maybeBurst(container);
      window.setInterval(function () {
        maybeBurst(container);
      }, BURST_INTERVAL_MS);
    }, INITIAL_DELAY_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
