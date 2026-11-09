// Scroll-driven motion for the posture-sec documentation sites.
// Inspired by the reveal patterns on land-book.com: elements enter with a
// gentle upward drift, siblings stagger, and the hero plays a staged sequence
// on load. No dependencies. Respects prefers-reduced-motion.
(() => {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  if (reduced.matches) return;

  // Mark the document so CSS knows motion is active.
  document.documentElement.dataset.motion = "";

  // --- Hero entrance ---
  // The hero plays immediately on load, not on scroll.
  const hero = document.querySelector(".hero");
  if (hero) {
    hero.classList.add("hero--enter");
    const targets = hero.querySelectorAll(
      ".eyebrow, .kicker, h1, .mega, .lede, .hero-actions, .cta-row, .hero-meta, .report, .term, .hero-side, .tel-stack"
    );
    targets.forEach((el, i) => {
      el.style.setProperty("--enter-i", i);
      el.classList.add("hero-enter");
    });
  }

  // --- Scroll reveals ---
  // Selectors that cover all three sites' structural patterns.
  const REVEAL_SELECTORS = [
    // Gauge
    ".section", ".rail-item", ".flow-card", ".ledger-row", ".card",
    ".code", ".report", ".limits",
    // Airlock
    ".sec", ".band", ".linkcard", ".stat", ".tel", ".split > .prose",
    ".family", ".rule",
    // Fixtures
    "section[id]", ".record", ".callout", ".entry", ".pair > .card",
    ".term", ".matrix-wrap", "dl.keys > div",
    // Shared
    ".section-head", ".cards > *", ".linkgrid > *", ".stats > *",
    "table", ".footer",
  ].join(", ");

  const seen = new WeakSet();
  const elements = [];

  document.querySelectorAll(REVEAL_SELECTORS).forEach((el) => {
    // Skip the hero (it has its own entrance).
    if (el.closest(".hero")) return;
    if (seen.has(el)) return;
    // Skip only direct children of another reveal target; the parent's
    // reveal already carries them. Deeper descendants reveal on their own.
    const parent = el.parentElement;
    if (parent && parent.matches(REVEAL_SELECTORS)) return;
    seen.add(el);
    elements.push(el);
  });

  // Assign stagger index within sibling groups.
  const groups = new Map();
  elements.forEach((el) => {
    const parent = el.parentElement;
    if (!groups.has(parent)) groups.set(parent, []);
    groups.get(parent).push(el);
  });
  groups.forEach((siblings) => {
    siblings.forEach((el, i) => {
      el.style.setProperty("--reveal-i", Math.min(i, 8));
    });
  });

  elements.forEach((el) => el.classList.add("reveal"));

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        el.classList.add("reveal--visible");
        observer.unobserve(el);
        // Once the reveal finishes, drop .reveal so hover transitions and
        // transforms on cards and rows are not stuck with the reveal timing.
        // Child transition events bubble, so only act on the element itself.
        // The timer covers the initial-paint race where no transition runs:
        // max stagger 560ms + 600ms duration + margin.
        const done = () => {
          el.classList.remove("reveal");
          el.removeEventListener("transitionend", onEnd);
          clearTimeout(timer);
        };
        const onEnd = (e) => {
          if (e.target === el) done();
        };
        const timer = setTimeout(done, 1400);
        el.addEventListener("transitionend", onEnd);
      });
    },
    { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
  );

  // defer scripts run before first paint, and a transition needs a painted
  // before-state. Observe after two frames so above-fold elements actually
  // drift in instead of appearing instantly with .reveal stuck on them.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      elements.forEach((el) => observer.observe(el));
    });
  });

  // --- Chip stagger ---
  // Shape chips and hero meta items cascade after their container enters.
  const chipGroups = new Map();
  document.querySelectorAll(".record-shapes li, .hero-meta li").forEach((el) => {
    const parent = el.parentElement;
    if (!chipGroups.has(parent)) chipGroups.set(parent, []);
    chipGroups.get(parent).push(el);
  });
  chipGroups.forEach((siblings) => {
    siblings.forEach((el, i) => {
      el.style.setProperty("--chip-i", Math.min(i, 10));
    });
  });

  // --- Parallax-lite on hero ---
  // A subtle vertical drift on the hero's visual object as the user scrolls
  // past it. Only active while the hero is in view.
  const heroVisual = hero && hero.querySelector(".report, .term, .hero-side");
  if (heroVisual) {
    // The entrance animation fills forwards and would override the inline
    // parallax transform forever, so drop the class once it finishes.
    heroVisual.addEventListener(
      "animationend",
      () => heroVisual.classList.remove("hero-enter"),
      { once: true }
    );
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const rect = hero.getBoundingClientRect();
        if (rect.bottom > 0 && rect.top < window.innerHeight) {
          const progress = Math.max(0, Math.min(1, -rect.top / rect.height));
          heroVisual.style.transform = `translateY(${progress * 18}px)`;
        }
        ticking = false;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
  }
})();