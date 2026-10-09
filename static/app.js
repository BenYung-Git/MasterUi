(() => {
  const state = {
    i18n: {},
    lang: "zh-TW",
    robots: { ids: [], items: [], next_id: "robot1" },
    groups: { ids: [], items: [], next_id: "group1" },
    tools: { ids: [], items: [], next_id: "tool1" },
    robotOriginalId: "",
    groupOriginalId: "",
    toolOriginalId: "",
    robotBeforeNew: null,
    groupBeforeNew: null,
    toolBeforeNew: null,
    robotIsNew: false,
    groupIsNew: false,
    toolIsNew: false,
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
    syncVisibleButtons("tool");
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
      const on = !!item.visible;
      opt.textContent = on
        ? `${item.id}  [${visibleLabel(true)}]`
        : `⊘ ${item.id}  [${visibleLabel(false)}]`;
      if (!on) opt.classList.add("is-disabled-item");
      selectEl.appendChild(opt);
    });
    if (selected && pack.ids.includes(selected)) {
      selectEl.value = selected;
    } else if (pack.ids.length) {
      selectEl.selectedIndex = 0;
    }
  }

  const POSE_FIELDS = [
    "tool_x", "tool_y", "tool_z", "tool_r", "tool_p", "tool_yaw",
    "vision_x", "vision_y", "vision_z", "vision_r", "vision_p", "vision_yaw",
    "ref_x", "ref_y", "ref_z",
  ];

  const NUM_PARTIAL_RE = /^-?\d*\.?\d*$/;
  const NUM_FULL_RE = /^-?(?:\d+\.?\d*|\.\d+)$/;

  function sanitizeNumberInput(value) {
    let s = String(value ?? "").replace(/[^\d.\-]/g, "");
    const neg = s.startsWith("-");
    s = s.replace(/-/g, "");
    const parts = s.split(".");
    s = parts.shift() || "";
    if (parts.length) s += "." + parts.join("").replace(/\./g, "");
    if (neg) s = "-" + s;
    return s;
  }

  function validatePoseNumbers(form) {
    for (const name of POSE_FIELDS) {
      const el = form.elements[name];
      if (!el) continue;
      const s = String(el.value ?? "").trim();
      if (s === "") continue;
      if (!NUM_FULL_RE.test(s) || !Number.isFinite(Number(s))) {
        throw new Error(t("msg_number_only"));
      }
    }
  }

  function bindNumericInputs() {
    document.querySelectorAll(".num-input").forEach((el) => {
      el.addEventListener("beforeinput", (e) => {
        if (e.inputType && e.inputType.startsWith("delete")) return;
        const data = e.data;
        if (data == null) return;
        const next =
          el.value.slice(0, el.selectionStart ?? el.value.length) +
          data +
          el.value.slice(el.selectionEnd ?? el.value.length);
        if (!NUM_PARTIAL_RE.test(next)) e.preventDefault();
      });
      el.addEventListener("input", () => {
        const cleaned = sanitizeNumberInput(el.value);
        if (el.value !== cleaned) el.value = cleaned;
      });
      el.addEventListener("paste", (e) => {
        e.preventDefault();
        const text = (e.clipboardData || window.clipboardData).getData("text");
        const cleaned = sanitizeNumberInput(text);
        const start = el.selectionStart ?? el.value.length;
        const end = el.selectionEnd ?? el.value.length;
        const next = sanitizeNumberInput(
          el.value.slice(0, start) + cleaned + el.value.slice(end)
        );
        el.value = next;
      });
    });
  }

  function syncEditableState(kind) {
    const map = {
      robot: {
        form: "#robotForm",
        card: "#robotCard",
        banner: "#robotDisabledBanner",
        save: "#robotSave",
        copy: "#robotCopy",
        isNew: () => state.robotIsNew,
      },
      group: {
        form: "#groupForm",
        card: "#groupCard",
        banner: "#groupDisabledBanner",
        save: "#groupSave",
        copy: "#groupCopy",
        isNew: () => state.groupIsNew,
      },
      tool: {
        form: "#toolForm",
        card: "#toolCard",
        banner: "#toolDisabledBanner",
        save: "#toolSave",
        copy: "#toolCopy",
        isNew: () => state.toolIsNew,
      },
    };
    const cfg = map[kind];
    const form = $(cfg.form);
    const visible = form.elements.visible.value === "true";
    const locked = !visible && !cfg.isNew();
    $(cfg.card).classList.toggle("is-disabled", locked);
    $(cfg.banner).classList.toggle("hidden", !locked);
    Array.from(form.elements).forEach((el) => {
      if (el.type === "hidden") return;
      if (el.id && /ToggleVisible$/.test(el.id)) return;
      el.disabled = locked;
    });
    $(cfg.save).disabled = locked;
    $(cfg.copy).disabled = locked;
  }

  function assertEditable(kind) {
    const form = $(
      kind === "robot" ? "#robotForm" : kind === "group" ? "#groupForm" : "#toolForm"
    );
    if (form.elements.visible.value !== "true") {
      throw new Error(t("msg_disabled_locked"));
    }
  }

  function renderLists() {
    renderList($("#robotList"), state.robots);
    renderList($("#groupList"), state.groups);
    renderList($("#toolList"), state.tools);
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

  const TOOL_FIELDS = [
    "id",
    "description",
    "note",
    "vision_id",
    "gripper_port",
    "tool_x",
    "tool_y",
    "tool_z",
    "tool_r",
    "tool_p",
    "tool_yaw",
    "vision_x",
    "vision_y",
    "vision_z",
    "vision_r",
    "vision_p",
    "vision_yaw",
    "ref_x",
    "ref_y",
    "ref_z",
  ];

  function fillToolForm(item) {
    const form = $("#toolForm");
    TOOL_FIELDS.forEach((f) => {
      const val = item?.[f];
      form.elements[f].value = val === undefined || val === null ? "" : String(val);
    });
    form.elements.original_id.value = item?.id ?? "";
    form.elements.visible.value = item ? String(!!item.visible) : "true";
    state.toolOriginalId = item?.id ?? "";
    state.toolIsNew = false;
    syncVisibleButtons("tool");
  }

  function syncVisibleButtons(kind) {
    const map = {
      robot: { form: "#robotForm", text: "#robotVisibleText", btn: "#robotToggleVisible" },
      group: { form: "#groupForm", text: "#groupVisibleText", btn: "#groupToggleVisible" },
      tool: { form: "#toolForm", text: "#toolVisibleText", btn: "#toolToggleVisible" },
    };
    const cfg = map[kind];
    const form = $(cfg.form);
    const textEl = $(cfg.text);
    const btn = $(cfg.btn);
    const visible = form.elements.visible.value === "true";
    textEl.textContent = visibleLabel(visible);
    textEl.classList.toggle("status-disabled", !visible);
    textEl.classList.toggle("status-enabled", visible);
    btn.textContent = visible ? t("btn_disable") : t("btn_enable");
    btn.dataset.mode = visible ? "disable" : "enable";
    btn.disabled = false;
    syncEditableState(kind);
  }

  async function reloadAll(selectRobotId, selectGroupId, selectToolId) {
    const settled = await Promise.allSettled([
      api("/api/robots"),
      api("/api/groups"),
      api("/api/tools"),
    ]);
    const errors = [];
    if (settled[0].status === "fulfilled") state.robots = settled[0].value;
    else errors.push(settled[0].reason);
    if (settled[1].status === "fulfilled") state.groups = settled[1].value;
    else errors.push(settled[1].reason);
    if (settled[2].status === "fulfilled") state.tools = settled[2].value;
    else errors.push(settled[2].reason);

    renderLists();

    const robots = state.robots;
    const groups = state.groups;
    const tools = state.tools;
    const rList = $("#robotList");
    const gList = $("#groupList");
    const tList = $("#toolList");
    if (selectRobotId && robots.ids.includes(selectRobotId)) {
      rList.value = selectRobotId;
    }
    if (selectGroupId && groups.ids.includes(selectGroupId)) {
      gList.value = selectGroupId;
    }
    if (selectToolId && tools.ids.includes(selectToolId)) {
      tList.value = selectToolId;
    }
    if (rList.value) fillRobotForm(findItem(robots, rList.value));
    else fillRobotForm(null);
    if (gList.value) fillGroupForm(findItem(groups, gList.value));
    else fillGroupForm(null);
    if (tList && tList.value) fillToolForm(findItem(tools, tList.value));
    else if (tList) fillToolForm(null);

    if (errors.length) {
      const err = errors[0];
      toast(String(err.message || err), true);
    }
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

  function formToToolPayload(form) {
    const payload = {
      id: form.elements.id.value.trim(),
      original_id: form.elements.original_id.value || null,
      visible: form.elements.visible.value === "true",
    };
    TOOL_FIELDS.forEach((f) => {
      if (f === "id") return;
      payload[f] = form.elements[f].value;
    });
    return payload;
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
      await reloadAll(target, $("#groupList").value || null, $("#toolList").value || null);
    });

    $("#robotSave").addEventListener("click", async () => {
      try {
        assertEditable("robot");
        const payload = formToRobotPayload($("#robotForm"));
        if (!payload.id) throw new Error(t("msg_id_required"));
        const res = await api("/api/robots", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        state.robotIsNew = false;
        await reloadAll(res.item.id, $("#groupList").value || null, $("#toolList").value || null);
        toast(t("msg_saved"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#robotCopy").addEventListener("click", async () => {
      const id = state.robotOriginalId || $("#robotList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        assertEditable("robot");
        const res = await api(`/api/robots/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll(res.id, $("#groupList").value || null, $("#toolList").value || null);
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
        await reloadAll(res.item.id, $("#groupList").value || null, $("#toolList").value || null);
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
      await reloadAll($("#robotList").value || null, target, $("#toolList").value || null);
    });

    $("#groupSave").addEventListener("click", async () => {
      try {
        assertEditable("group");
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
        await reloadAll($("#robotList").value || null, res.item.id, $("#toolList").value || null);
        toast(t("msg_saved"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#groupCopy").addEventListener("click", async () => {
      const id = state.groupOriginalId || $("#groupList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        assertEditable("group");
        const res = await api(`/api/groups/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll($("#robotList").value || null, res.id, $("#toolList").value || null);
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
        await reloadAll($("#robotList").value || null, res.item.id, $("#toolList").value || null);
        toast(mode === "disable" ? t("msg_soft_deleted") : t("msg_restored"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });
  }

  function bindToolActions() {
    $("#toolList").addEventListener("change", () => {
      const item = findItem(state.tools, $("#toolList").value);
      fillToolForm(item);
    });

    $("#toolNew").addEventListener("click", () => {
      state.toolBeforeNew = state.toolOriginalId || state.tools.ids[0] || null;
      state.toolIsNew = true;
      $("#toolList").selectedIndex = -1;
      fillToolForm({
        id: state.tools.next_id,
        visible: true,
      });
      state.toolIsNew = true;
      $("#toolForm").elements.original_id.value = "";
    });

    $("#toolCancel").addEventListener("click", async () => {
      const target = state.toolIsNew
        ? state.toolBeforeNew
        : state.toolOriginalId || state.tools.ids[0];
      state.toolIsNew = false;
      state.toolBeforeNew = null;
      await reloadAll(
        $("#robotList").value || null,
        $("#groupList").value || null,
        target
      );
    });

    $("#toolSave").addEventListener("click", async () => {
      try {
        assertEditable("tool");
        const form = $("#toolForm");
        validatePoseNumbers(form);
        const payload = formToToolPayload(form);
        if (!payload.id) throw new Error(t("msg_id_required"));
        const res = await api("/api/tools", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        state.toolIsNew = false;
        await reloadAll(
          $("#robotList").value || null,
          $("#groupList").value || null,
          res.item.id
        );
        toast(t("msg_saved"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#toolCopy").addEventListener("click", async () => {
      const id = state.toolOriginalId || $("#toolList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        assertEditable("tool");
        const res = await api(`/api/tools/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll(
          $("#robotList").value || null,
          $("#groupList").value || null,
          res.id
        );
        toast(t("msg_copied").replace("{id}", res.id));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#toolToggleVisible").addEventListener("click", async () => {
      const id = state.toolOriginalId || $("#toolList").value;
      if (!id || state.toolIsNew) return toast(t("msg_select_first"), true);
      const mode = $("#toolToggleVisible").dataset.mode;
      if (mode === "disable") {
        if (!confirm(t("msg_confirm_soft_delete").replace("{id}", id))) return;
      }
      try {
        const path = mode === "disable" ? "disable" : "enable";
        const res = await api(`/api/tools/${encodeURIComponent(id)}/${path}`, {
          method: "POST",
        });
        await reloadAll(
          $("#robotList").value || null,
          $("#groupList").value || null,
          res.item.id
        );
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
    bindNumericInputs();
    bindRobotActions();
    bindGroupActions();
    bindToolActions();
    await reloadAll(null, null, null);
  }

  boot().catch((err) => toast(String(err.message || err), true));
})();
