// stellar-account-fixtures client runtime
// Zero dependencies: instant search, network tabs, code & hash copy, and system-aware theme toggle.

// Copy button for code blocks with fallback selection
(() => {
  const blocks = document.querySelectorAll("[data-copy]");
  for (const block of blocks) {
    const pre = block.querySelector("pre");
    const label = block.querySelector(".code-label") || block.querySelector(".term-head");
    if (!pre || !label || label.querySelector(".copy")) continue;

    const button = document.createElement("button");
    button.className = "copy";
    button.type = "button";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code to clipboard");

    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(pre.innerText);
        button.textContent = "Copied";
        button.dataset.copied = "true";
      } catch {
        button.textContent = "Select";
        const range = document.createRange();
        range.selectNodeContents(pre);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        return;
      }
      window.setTimeout(() => {
        button.textContent = "Copy";
        delete button.dataset.copied;
      }, 1600);
    });

    label.appendChild(button);
  }
})();

// One-click SHA-256 hash copy on fixture records
(() => {
  const proofDds = document.querySelectorAll(".record-proof dd[data-sha256]");
  for (const dd of proofDds) {
    const fullHash = dd.getAttribute("data-sha256");
    if (!fullHash) continue;

    dd.setAttribute("title", `Full SHA-256: ${fullHash} (click to copy)`);
    dd.style.cursor = "pointer";

    dd.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(fullHash);
        const originalText = dd.textContent;
        dd.textContent = "Copied!";
        dd.classList.add("is-copied");
        setTimeout(() => {
          dd.textContent = originalText;
          dd.classList.remove("is-copied");
        }, 1500);
      } catch {
        // Fallback: select text
        const range = document.createRange();
        range.selectNodeContents(dd);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
    });
  }
})();

// Instant Record Filtering & Search (Overview page)
(() => {
  const records = Array.from(document.querySelectorAll(".record"));
  if (!records.length) return;

  const searchInput = document.getElementById("record-search");
  const filterPills = Array.from(document.querySelectorAll(".filter-pill"));
  let activeFilter = "all";
  let searchQuery = "";

  const applyFilters = () => {
    let visibleCount = 0;
    records.forEach((record) => {
      const network = (record.querySelector(".net")?.getAttribute("data-network") || "").toLowerCase();
      const fixtureName = (record.getAttribute("data-fixture") || "").toLowerCase();
      const ledger = (record.querySelector("[data-ledger]")?.textContent || "").toLowerCase();
      const why = (record.querySelector(".record-why")?.textContent || "").toLowerCase();
      const shapes = Array.from(record.querySelectorAll(".chip")).map((c) => c.textContent.toLowerCase()).join(" ");
      
      const matchesNetwork = activeFilter === "all" || network === activeFilter;
      const matchesSearch = !searchQuery || 
        fixtureName.includes(searchQuery) || 
        ledger.includes(searchQuery) || 
        why.includes(searchQuery) || 
        shapes.includes(searchQuery);

      if (matchesNetwork && matchesSearch) {
        record.style.display = "";
        visibleCount++;
      } else {
        record.style.display = "none";
      }
    });

    const emptyNotice = document.getElementById("records-empty");
    if (emptyNotice) {
      emptyNotice.style.display = visibleCount === 0 ? "block" : "none";
    }
  };

  filterPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      filterPills.forEach((p) => p.classList.remove("is-active"));
      pill.classList.add("is-active");
      activeFilter = pill.getAttribute("data-filter") || "all";
      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value.trim().toLowerCase();
      applyFilters();
    });
  }
})();

// Theme management: Stellar Cosmic Dark default, Architectural Slate/Ice Light mode
(() => {
  const KEY = "corpus-theme";
  const root = document.documentElement;
  const toggle = root.querySelector(".theme-toggle");
  if (!toggle) return;

  const read = (key) => {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  };

  const write = (key, value) => {
    try {
      window.localStorage.setItem(key, value);
    } catch {}
  };

  const paint = (theme) => {
    const current = theme === "light" ? "light" : "dark";
    root.dataset.theme = current;
    const target = current === "light" ? "dark" : "light";
    const text = toggle.querySelector("span");
    if (text) text.textContent = target === "light" ? "Light" : "Dark";
    toggle.setAttribute("aria-label", `Switch to ${target} theme`);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", current === "light" ? "#f8fafc" : "#060913");
  };

  toggle.addEventListener("click", () => {
    const next = root.dataset.theme === "light" ? "dark" : "light";
    write(KEY, next);
    paint(next);
  });

  paint(root.dataset.theme);

  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", (event) => {
    if (read(KEY)) return;
    paint(event.matches ? "light" : "dark");
  });
})();
