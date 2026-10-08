(() => {
  const state = {
    i18n: {},
    lang: "zh-TW",
    robots: { ids: [], items: [], next_id: "robot1" },
    groups: { ids: [], items: [], next_id: "group1" },
    robotOriginalId: "",
    groupOriginalId: "",
    robotBeforeNew: null,
    groupBeforeNew: null,
    robotIsNew: false,
    groupIsNew: false,
  };

  const $ = (sel) => document.querySelector(sel);

  function t(key) {
    return state.i18n[state.lang]?.[key] ?? key;
  }

  function toast(msg, isError = false) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.toggle("error", !!isError);
    el.classList.remove("hidden");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => el.classList.add("hidden"), 2200);
  }

  async function api(url, options) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || res.statusText);
    }
    return data;
  }

  function applyI18n() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      el.textContent = t(key);
    });
    document.title = t("app_title");
    fillLangSelect();
    renderLists();
    syncVisibleButtons("robot");
    syncVisibleButtons("group");
  }

  function fillLangSelect() {
    const sel = $("#langSelect");
    const codes = ["zh-TW", "en", "zh-CN"];
    const labels = {
      "zh-TW": t("lang_zh_tw"),
      en: t("lang_en"),
      "zh-CN": t("lang_zh_cn"),
    };
    sel.innerHTML = "";
    codes.forEach((code) => {
      if (!state.i18n[code]) return;
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = labels[code];
      if (code === state.lang) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  function visibleLabel(visible) {
    return visible ? t("visible_true") : t("visible_false");
  }

  function renderList(selectEl, pack) {
    const selected = selectEl.value;
    selectEl.innerHTML = "";
    pack.items.forEach((item) => {
      const opt = document.createElement("option");
      opt.value = item.id;
      opt.textContent = `${item.id}  [${visibleLabel(!!item.visible)}]`;
      selectEl.appendChild(opt);
    });
    if (selected && pack.ids.includes(selected)) {
      selectEl.value = selected;
    } else if (pack.ids.length) {
      selectEl.selectedIndex = 0;
    }
  }

  function renderLists() {
    renderList($("#robotList"), state.robots);
    renderList($("#groupList"), state.groups);
  }

  function findItem(pack, id) {
    return pack.items.find((x) => x.id === id) || null;
  }

  function fillRobotForm(item) {
    const form = $("#robotForm");
    const fields = [
      "id",
      "ip",
      "maker",
      "product",
      "arm",
      "cab",
      "version_scb",
      "version_controller",
      "version_servo",
      "payload",
    ];
    fields.forEach((f) => {
      form.elements[f].value = item?.[f] ?? "";
    });
    form.elements.original_id.value = item?.id ?? "";
    form.elements.visible.value = item ? String(!!item.visible) : "true";
    state.robotOriginalId = item?.id ?? "";
    state.robotIsNew = false;
    syncVisibleButtons("robot");
  }

  function fillGroupForm(item) {
    const form = $("#groupForm");
    form.elements.id.value = item?.id ?? "";
    form.elements.maker.value = item?.maker ?? "robot_team";
    form.elements.robots.value = item?.robots ?? "";
    form.elements.original_id.value = item?.id ?? "";
    form.elements.visible.value = item ? String(!!item.visible) : "true";
    state.groupOriginalId = item?.id ?? "";
    state.groupIsNew = false;
    syncVisibleButtons("group");
  }

  function syncVisibleButtons(kind) {
    const form = $(kind === "robot" ? "#robotForm" : "#groupForm");
    const textEl = $(kind === "robot" ? "#robotVisibleText" : "#groupVisibleText");
    const btn = $(kind === "robot" ? "#robotToggleVisible" : "#groupToggleVisible");
    const visible = form.elements.visible.value === "true";
    textEl.textContent = visibleLabel(visible);
    btn.textContent = visible ? t("btn_disable") : t("btn_enable");
    btn.dataset.mode = visible ? "disable" : "enable";
  }

  async function reloadAll(selectRobotId, selectGroupId) {
    const [robots, groups] = await Promise.all([
      api("/api/robots"),
      api("/api/groups"),
    ]);
    state.robots = robots;
    state.groups = groups;
    renderLists();

    const rList = $("#robotList");
    const gList = $("#groupList");
    if (selectRobotId && robots.ids.includes(selectRobotId)) {
      rList.value = selectRobotId;
    }
    if (selectGroupId && groups.ids.includes(selectGroupId)) {
      gList.value = selectGroupId;
    }
    if (rList.value) fillRobotForm(findItem(robots, rList.value));
    else fillRobotForm(null);
    if (gList.value) fillGroupForm(findItem(groups, gList.value));
    else fillGroupForm(null);
  }

  function bindTabs() {
    document.querySelectorAll(".tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
        document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        $(`#panel-${btn.dataset.tab}`).classList.add("active");
      });
    });
  }

  function bindChrome() {
    $("#langSelect").addEventListener("change", (e) => {
      state.lang = e.target.value;
      localStorage.setItem("master_lang", state.lang);
      applyI18n();
    });
    $("#fontSelect").addEventListener("change", (e) => {
      const size = e.target.value;
      document.documentElement.style.setProperty("--font", `${size}px`);
      localStorage.setItem("master_font", size);
    });
  }

  function formToRobotPayload(form) {
    return {
      id: form.elements.id.value.trim(),
      original_id: form.elements.original_id.value || null,
      ip: form.elements.ip.value,
      maker: form.elements.maker.value,
      product: form.elements.product.value,
      arm: form.elements.arm.value,
      cab: form.elements.cab.value,
      version_scb: form.elements.version_scb.value,
      version_controller: form.elements.version_controller.value,
      version_servo: form.elements.version_servo.value,
      payload: form.elements.payload.value,
      visible: form.elements.visible.value === "true",
    };
  }

  function bindRobotActions() {
    $("#robotList").addEventListener("change", () => {
      const item = findItem(state.robots, $("#robotList").value);
      fillRobotForm(item);
    });

    $("#robotNew").addEventListener("click", () => {
      state.robotBeforeNew = state.robotOriginalId || state.robots.ids[0] || null;
      state.robotIsNew = true;
      $("#robotList").selectedIndex = -1;
      fillRobotForm({
        id: state.robots.next_id,
        visible: true,
      });
      state.robotIsNew = true;
      $("#robotForm").elements.original_id.value = "";
    });

    $("#robotCancel").addEventListener("click", async () => {
      const target = state.robotIsNew
        ? state.robotBeforeNew
        : state.robotOriginalId || state.robots.ids[0];
      state.robotIsNew = false;
      state.robotBeforeNew = null;
      await reloadAll(target, $("#groupList").value || null);
    });

    $("#robotSave").addEventListener("click", async () => {
      try {
        const payload = formToRobotPayload($("#robotForm"));
        if (!payload.id) throw new Error(t("msg_id_required"));
        const res = await api("/api/robots", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        state.robotIsNew = false;
        await reloadAll(res.item.id, $("#groupList").value || null);
        toast(t("msg_saved"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#robotCopy").addEventListener("click", async () => {
      const id = state.robotOriginalId || $("#robotList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        const res = await api(`/api/robots/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll(res.id, $("#groupList").value || null);
        toast(t("msg_copied").replace("{id}", res.id));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#robotToggleVisible").addEventListener("click", async () => {
      const id = state.robotOriginalId || $("#robotList").value;
      if (!id || state.robotIsNew) return toast(t("msg_select_first"), true);
      const mode = $("#robotToggleVisible").dataset.mode;
      if (mode === "disable") {
        if (!confirm(t("msg_confirm_soft_delete").replace("{id}", id))) return;
      }
      try {
        const path = mode === "disable" ? "disable" : "enable";
        const res = await api(`/api/robots/${encodeURIComponent(id)}/${path}`, {
          method: "POST",
        });
        await reloadAll(res.item.id, $("#groupList").value || null);
        toast(mode === "disable" ? t("msg_soft_deleted") : t("msg_restored"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });
  }

  function bindGroupActions() {
    $("#groupList").addEventListener("change", () => {
      const item = findItem(state.groups, $("#groupList").value);
      fillGroupForm(item);
    });

    $("#groupNew").addEventListener("click", () => {
      state.groupBeforeNew = state.groupOriginalId || state.groups.ids[0] || null;
      state.groupIsNew = true;
      $("#groupList").selectedIndex = -1;
      fillGroupForm({
        id: state.groups.next_id,
        maker: "robot_team",
        robots: "",
        visible: true,
      });
      state.groupIsNew = true;
      $("#groupForm").elements.original_id.value = "";
    });

    $("#groupCancel").addEventListener("click", async () => {
      const target = state.groupIsNew
        ? state.groupBeforeNew
        : state.groupOriginalId || state.groups.ids[0];
      state.groupIsNew = false;
      state.groupBeforeNew = null;
      await reloadAll($("#robotList").value || null, target);
    });

    $("#groupSave").addEventListener("click", async () => {
      try {
        const form = $("#groupForm");
        const payload = {
          id: form.elements.id.value.trim(),
          original_id: form.elements.original_id.value || null,
          maker: form.elements.maker.value,
          robots: form.elements.robots.value,
          visible: form.elements.visible.value === "true",
        };
        if (!payload.id) throw new Error(t("msg_id_required"));
        const res = await api("/api/groups", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        state.groupIsNew = false;
        await reloadAll($("#robotList").value || null, res.item.id);
        toast(t("msg_saved"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#groupCopy").addEventListener("click", async () => {
      const id = state.groupOriginalId || $("#groupList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        const res = await api(`/api/groups/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll($("#robotList").value || null, res.id);
        toast(t("msg_copied").replace("{id}", res.id));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#groupToggleVisible").addEventListener("click", async () => {
      const id = state.groupOriginalId || $("#groupList").value;
      if (!id || state.groupIsNew) return toast(t("msg_select_first"), true);
      const mode = $("#groupToggleVisible").dataset.mode;
      if (mode === "disable") {
        if (!confirm(t("msg_confirm_soft_delete").replace("{id}", id))) return;
      }
      try {
        const path = mode === "disable" ? "disable" : "enable";
        const res = await api(`/api/groups/${encodeURIComponent(id)}/${path}`, {
          method: "POST",
        });
        await reloadAll($("#robotList").value || null, res.item.id);
        toast(mode === "disable" ? t("msg_soft_deleted") : t("msg_restored"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });
  }

  async function boot() {
    state.lang = localStorage.getItem("master_lang") || "zh-TW";
    const font = localStorage.getItem("master_font") || "12";
    $("#fontSelect").value = font;
    document.documentElement.style.setProperty("--font", `${font}px`);

    state.i18n = await api("/api/i18n");
    if (!state.i18n[state.lang]) state.lang = "zh-TW";
    applyI18n();
    bindTabs();
    bindChrome();
    bindRobotActions();
    bindGroupActions();
    await reloadAll(null, null);
  }

  boot().catch((err) => toast(String(err.message || err), true));
})();
