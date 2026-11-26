(() => {
  const PAGE_SIZE = 60;
  const CATS = [
    "all", "installed", "review", "editor", "language",
    "stats", "ui", "scheduling", "sync", "browser", "media", "tools"
  ];

  const state = {
    lang: "zh",
    i18n: {},
    items: [],
    total: 0,
    counts: {},
    source: "",
    compatOnly: false,
    activeOnly: false,
    category: "all",
    sortBy: "popular",
    sortDir: "desc",
    query: "",
    limit: PAGE_SIZE,
    activeId: null,
    installingId: null,
    detailReviews: [],
    reviewFilter: "all",
    reviewLimit: 30,
    controlsBound: false,
  };

  const $ = (id) => document.getElementById(id);
  const tr = (k, vars) => {
    let s = state.i18n[k] || k;
    if (vars) {
      for (const [vk, vv] of Object.entries(vars)) {
        s = s.replaceAll(`{${vk}}`, String(vv));
      }
    }
    return s;
  };
  const send = (payload) => {
    if (typeof pycmd === "function") {
      pycmd("store:" + JSON.stringify(payload));
    } else {
      setTimeout(() => send(payload), 30);
    }
  };
  const esc = (s) => String(s || "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c]
  ));
  const fmtDate = (ts) => {
    if (!ts) return "—";
    const d = new Date(ts * 1000);
    return isNaN(d.getTime()) ? "—" : d.toISOString().slice(0, 10);
  };
  const compatClass = (c) => (
    c === "compatible" ? "ok" : c === "likely" ? "accent" : c === "incompatible" ? "bad" : c === "legacy" ? "warn" : ""
  );
  const summaryOf = (it) => (state.lang === "zh" ? (it.summary_zh || it.summary_en) : (it.summary_en || it.summary_zh)) || "";

  let searchTimer = null;

  function initControls() {
    $("brand-title").textContent = tr("win_title");
    $("search-input").placeholder = tr("search_ph");
    $("btn-compat").textContent = tr("flt_compat");
    $("btn-active").textContent = tr("flt_active");
    $("btn-updates").textContent = tr("btn_updates");
    $("btn-refresh").textContent = tr("btn_refresh");

    const sortSel = $("sort-select");
    sortSel.innerHTML = [
      ["popular", tr("sort_popular")],
      ["rating", tr("sort_rating")],
      ["updated", tr("sort_updated")],
      ["name", tr("sort_name")],
    ].map(([v, label]) => `<option value="${v}">${esc(label)}</option>`).join("");
    sortSel.value = state.sortBy;
    const renderSortDir = () => {
      $("btn-sort-dir").textContent = tr(state.sortDir === "asc" ? "sort_asc" : "sort_desc");
    };
    renderSortDir();

    if (state.controlsBound) return;
    state.controlsBound = true;

    $("search-input").addEventListener("input", (e) => {
      state.query = e.target.value || "";
      state.limit = PAGE_SIZE;
      clearTimeout(searchTimer);
      searchTimer = setTimeout(requestQuery, 120);
    });
    $("btn-compat").addEventListener("click", () => {
      state.compatOnly = !state.compatOnly;
      $("btn-compat").classList.toggle("active", state.compatOnly);
      state.limit = PAGE_SIZE;
      requestQuery();
    });
    $("btn-active").addEventListener("click", () => {
      state.activeOnly = !state.activeOnly;
      $("btn-active").classList.toggle("active", state.activeOnly);
      state.limit = PAGE_SIZE;
      requestQuery();
    });
    sortSel.addEventListener("change", (e) => {
      state.sortBy = e.target.value;
      state.sortDir = state.sortBy === "name" ? "asc" : "desc";
      renderSortDir();
      state.limit = PAGE_SIZE;
      requestQuery();
    });
    $("btn-sort-dir").addEventListener("click", () => {
      state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      renderSortDir();
      state.limit = PAGE_SIZE;
      requestQuery();
    });
    $("btn-updates").addEventListener("click", () => send({ action: "check_updates" }));
    $("btn-refresh").addEventListener("click", () => {
      setStatus(tr("loading"));
      send({ action: "refresh_catalog" });
    });
    $("btn-load-more").addEventListener("click", () => {
      state.limit += PAGE_SIZE;
      requestQuery();
    });
    $("drawer-close").addEventListener("click", closeDrawer);
    $("drawer-backdrop").addEventListener("click", closeDrawer);
    $("drawer-desc").addEventListener("click", (e) => {
      const a = e.target.closest("a");
      if (a && a.href && a.href.startsWith("http")) {
        e.preventDefault();
        send({ action: "open_url", url: a.href });
      }
    });
  }

  function requestQuery() {
    send({
      action: "query",
      query: state.query,
      category: state.category,
      compat_only: state.compatOnly,
      active_only: state.activeOnly,
      sort_by: state.sortBy,
      sort_dir: state.sortDir,
      limit: state.limit,
    });
  }

  function setStatus(msg) {
    $("status-msg").textContent = msg || "";
  }

  function renderSidebar() {
    const html = CATS.map((cat) => {
      const cnt = state.counts[cat] ?? 0;
      const active = state.category === cat ? "active" : "";
      return `<button class="cat-btn ${active}" data-cat="${cat}" type="button">
        <span>${esc(tr("cat_" + cat))}</span>
        <span class="cat-cnt">${cnt}</span>
      </button>`;
    }).join("");
    const nav = $("cat-list");
    nav.innerHTML = html;
    nav.querySelectorAll(".cat-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.category = btn.dataset.cat;
        state.limit = PAGE_SIZE;
        renderSidebar();
        requestQuery();
      });
    });
    $("source-badge").textContent = state.source ? tr("source_" + state.source) : "";
  }

  function actionBtnHtml(it) {
    const sid = String(it.id);
    if (state.installingId === sid) {
      return `<button class="btn btn-sm" disabled>${esc(tr("btn_installing"))}</button>`;
    }
    if (it.installed) {
      const cls = it.enabled ? "ok" : "warn";
      const lbl = it.enabled ? tr("lbl_installed") : tr("lbl_disabled");
      return `<span class="badge ${cls}">${esc(lbl)}</span>`;
    }
    return `<button class="btn btn-primary btn-sm" data-install="${sid}" type="button">${esc(tr("btn_install"))}</button>`;
  }

  function renderGrid() {
    const total = Number(state.total ?? state.items.length);
    const shownItems = state.items;
    $("count-label").textContent = tr("count_shown", { shown: shownItems.length, total });

    const grid = $("card-grid");
    const empty = $("empty-state");
    if (!total || !shownItems.length) {
      grid.innerHTML = "";
      empty.textContent = tr("empty_results");
      empty.classList.remove("hidden");
      $("btn-load-more").classList.add("hidden");
      return;
    }
    empty.classList.add("hidden");

    grid.innerHTML = shownItems.map((it) => {
      const sum = summaryOf(it);
      const pct = it.rating_pct != null ? `${it.rating_pct}%` : "";
      const cCls = compatClass(it.compat);
      return `<div class="card" data-id="${it.id}">
        <div class="card-head">
          <div class="card-title">${esc(it.title)}</div>
          ${actionBtnHtml(it)}
        </div>
        ${sum ? `<div class="card-summary">${esc(sum)}</div>` : ""}
        <div class="card-badges">
          <span class="badge">${esc(tr("cat_" + (it.category || "tools")))}</span>
          <span class="badge ${cCls}">${esc(tr("compat_" + (it.compat || "unknown")))}</span>
          <span class="badge">${esc(tr("act_" + (it.activity || "stale")))}</span>
        </div>
        <div class="card-foot">
          <span>👍 ${it.likes || 0}${it.dislikes ? ` / 👎 ${it.dislikes}` : ""}${pct ? ` (${pct})` : ""}</span>
          <span>${fmtDate(it.modified)}${it.max_version ? ` · ${esc(it.max_version)}` : ""}</span>
        </div>
      </div>`;
    }).join("");

    grid.querySelectorAll("[data-install]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = btn.dataset.install;
        state.installingId = id;
        renderGrid();
        send({ action: "install", id: Number(id) });
      });
    });
    grid.querySelectorAll(".card").forEach((card) => {
      card.addEventListener("click", () => openDrawer(Number(card.dataset.id)));
    });

    const rem = total - shownItems.length;
    const moreBtn = $("btn-load-more");
    if (rem > 0) {
      moreBtn.textContent = tr("btn_load_more", { n: rem });
      moreBtn.classList.remove("hidden");
    } else {
      moreBtn.classList.add("hidden");
    }
  }

  function openDrawer(id) {
    state.activeId = id;
    const it = state.items.find((x) => Number(x.id) === id);
    if (!it) return;
    $("drawer-title").textContent = it.title || String(id);
    $("drawer-badges").innerHTML = `
      <span class="badge">${esc(tr("cat_" + (it.category || "tools")))}</span>
      <span class="badge ${compatClass(it.compat)}">${esc(tr("compat_" + (it.compat || "unknown")))}</span>
      <span class="badge">${esc(tr("act_" + (it.activity || "stale")))}</span>`;
    renderDrawerActions(it, "");
    $("drawer-meta").innerHTML = `
      <div>${esc(tr("lbl_code"))}: <b>${id}</b></div>
      <div>${esc(tr("lbl_reviews"))}: 👍 ${it.likes || 0} / 👎 ${it.dislikes || 0}</div>
      <div>${esc(tr("lbl_updated"))}: ${fmtDate(it.modified)}</div>
      <div>${esc(tr("lbl_anki_ver"))}: ${esc(it.max_version || "—")}</div>`;
    $("drawer-tags").innerHTML = "";
    $("drawer-desc").innerHTML = `<span class="badge">${esc(tr("loading_detail"))}</span>`;
    state.detailReviews = [];
    state.reviewFilter = "all";
    state.reviewLimit = 30;
    $("drawer-reviews").classList.add("hidden");
    $("drawer-reviews").innerHTML = "";
    $("drawer-backdrop").classList.remove("hidden");
    $("detail-drawer").classList.remove("hidden");
    send({ action: "fetch_detail", id });
  }

  function renderReviews() {
    const box = $("drawer-reviews");
    const all = state.detailReviews || [];
    const filtered = state.reviewFilter === "pos"
      ? all.filter((r) => r.positive)
      : state.reviewFilter === "neg"
        ? all.filter((r) => !r.positive)
        : all;
    const shown = filtered.slice(0, state.reviewLimit);
    const awUrl = `https://ankiweb.net/shared/info/${state.activeId}`;

    const hdr = `<div class="reviews-head">
      <span class="reviews-title">${esc(tr("sec_reviews", { n: all.length }))}</span>
      <div class="reviews-filters">
        <button class="pill-btn btn-sm ${state.reviewFilter === "all" ? "active" : ""}" data-rf="all" type="button">${esc(tr("rev_all"))}</button>
        <button class="pill-btn btn-sm ${state.reviewFilter === "pos" ? "active" : ""}" data-rf="pos" type="button">${esc(tr("rev_pos"))}</button>
        <button class="pill-btn btn-sm ${state.reviewFilter === "neg" ? "active" : ""}" data-rf="neg" type="button">${esc(tr("rev_neg"))}</button>
        <button class="btn btn-sm" id="btn-write-rev" type="button">${esc(tr("btn_write_review"))}</button>
      </div>
    </div>`;

    const listHtml = shown.length
      ? shown.map((r) => {
          const icon = r.positive ? '<span class="badge ok">👍</span>' : '<span class="badge bad">👎</span>';
          const reply = r.author_reply
            ? `<div class="review-reply"><div class="review-reply-hdr">${esc(tr("author_reply"))}${r.reply_created ? ` · ${fmtDate(r.reply_created)}` : ""}</div><div>${esc(r.author_reply)}</div></div>`
            : "";
          return `<div class="review-item">
            <div class="review-meta">${icon}<span>${fmtDate(r.created)}</span></div>
            <div class="review-body">${esc(r.text)}</div>
            ${reply}
          </div>`;
        }).join("")
      : `<div class="badge">${esc(tr("no_reviews"))}</div>`;

    const more = filtered.length - shown.length;
    const moreHtml = more > 0
      ? `<button class="btn btn-sm" id="btn-more-rev" type="button">${esc(tr("btn_load_more", { n: more }))}</button>`
      : "";

    box.innerHTML = hdr + listHtml + moreHtml;
    box.classList.remove("hidden");
    box.querySelectorAll("[data-rf]").forEach((b) => {
      b.onclick = () => { state.reviewFilter = b.dataset.rf; state.reviewLimit = 30; renderReviews(); };
    });
    if ($("btn-write-rev")) $("btn-write-rev").onclick = () => send({ action: "open_url", url: awUrl });
    if ($("btn-more-rev")) $("btn-more-rev").onclick = () => { state.reviewLimit += 30; renderReviews(); };
  }

  function renderDrawerActions(it, detail) {
    const sid = String(it.id);
    const awUrl = (detail && detail.ankiweb_url) || `https://ankiweb.net/shared/info/${sid}`;
    const ghUrl = detail && detail.github_url;
    const supUrl = detail && detail.support_url;
    const btns = [];
    if (it.installed) {
      btns.push(`<button class="btn" id="d-toggle" type="button">${esc(tr(it.enabled ? "btn_disable" : "btn_enable"))}</button>`);
      btns.push(`<button class="btn btn-danger" id="d-del" type="button">${esc(tr("btn_uninstall"))}</button>`);
    } else {
      const dis = state.installingId === sid ? "disabled" : "";
      const lbl = state.installingId === sid ? tr("btn_installing") : tr("btn_install");
      btns.push(`<button class="btn btn-primary" id="d-inst" ${dis} type="button">${esc(lbl)}</button>`);
    }
    btns.push(`<button class="btn" data-url="${esc(awUrl)}" type="button">${esc(tr("btn_ankiweb"))}</button>`);
    if (ghUrl) btns.push(`<button class="btn" data-url="${esc(ghUrl)}" type="button">${esc(tr("btn_github"))}</button>`);
    else if (supUrl && supUrl.startsWith("http")) btns.push(`<button class="btn" data-url="${esc(supUrl)}" type="button">${esc(tr("btn_support"))}</button>`);

    const box = $("drawer-actions");
    box.innerHTML = btns.join("");
    if ($("d-inst")) $("d-inst").onclick = () => { state.installingId = sid; renderDrawerActions(it, detail); renderGrid(); send({ action: "install", id: Number(sid) }); };
    if ($("d-toggle")) $("d-toggle").onclick = () => send({ action: "toggle", id: sid });
    if ($("d-del")) $("d-del").onclick = () => send({ action: "uninstall", id: sid, title: it.title });
    box.querySelectorAll("[data-url]").forEach((b) => {
      b.onclick = () => send({ action: "open_url", url: b.dataset.url });
    });
  }

  function closeDrawer() {
    state.activeId = null;
    $("drawer-backdrop").classList.add("hidden");
    $("detail-drawer").classList.add("hidden");
  }

  window.__storeReceive = (msg) => {
    if (!msg || !msg.type) return;
    if (msg.type === "init") {
      state.lang = msg.lang || "zh";
      state.i18n = msg.i18n || {};
      if (msg.night) document.body.classList.add("night-mode");
      initControls();
      renderSidebar();
    } else if (msg.type === "catalog") {
      state.items = msg.items || [];
      state.total = msg.total ?? state.items.length;
      state.counts = msg.counts || {};
      state.source = msg.source || "";
      setStatus(msg.warning || "");
      renderSidebar();
      renderGrid();
      if (state.activeId != null) {
        const cur = state.items.find((x) => Number(x.id) === state.activeId);
        if (cur) renderDrawerActions(cur, null);
      }
    } else if (msg.type === "detail") {
      if (Number(msg.id) !== state.activeId) return;
      const d = msg.detail || {};
      const it = state.items.find((x) => Number(x.id) === state.activeId) || { id: msg.id };
      renderDrawerActions(it, d);
      const vers = (d.branches || []).map((b) => b.version_range).join(", ") || it.max_version || "—";
      const sizeText = d.size_bytes ? `${(d.size_bytes / 1024).toFixed(1)} KB` : "—";
      $("drawer-meta").innerHTML = `
        <div>${esc(tr("lbl_code"))}: <b>${d.id}</b></div>
        <div>${esc(tr("lbl_reviews"))}: 👍 ${d.likes ?? it.likes ?? 0} / 👎 ${d.dislikes ?? it.dislikes ?? 0}</div>
        <div>${esc(tr("lbl_updated"))}: ${fmtDate(d.modified || it.modified)}</div>
        <div>${esc(tr("lbl_anki_ver"))}: ${esc(vers)}</div>
        <div>${esc(tr("lbl_size"))}: ${esc(sizeText)}</div>`;
      $("drawer-tags").innerHTML = (d.tags || []).map((t) => `<span class="badge accent">#${esc(t)}</span>`).join("");
      $("drawer-desc").innerHTML = d.description_html || "—";
      state.detailReviews = d.reviews || [];
      renderReviews();
    } else if (msg.type === "detail_error") {
      if (Number(msg.id) !== state.activeId) return;
      $("drawer-desc").innerHTML = `<div class="detail-error"><span>${esc(tr("detail_load_fail", { err: msg.error || "" }))}</span><button class="btn btn-sm" id="d-retry" type="button">${esc(tr("btn_retry"))}</button></div>`;
      if ($("d-retry")) {
        $("d-retry").onclick = () => {
          $("drawer-desc").innerHTML = `<span class="badge">${esc(tr("loading_detail"))}</span>`;
          send({ action: "fetch_detail", id: state.activeId, force: true });
        };
      }
    } else if (msg.type === "install_done") {
      state.installingId = null;
      setStatus(msg.ok ? tr("msg_restart") : tr("msg_install_fail", { err: msg.error || "" }));
      requestQuery();
    } else if (msg.type === "status") {
      setStatus(msg.message || "");
    }
  };
})();
