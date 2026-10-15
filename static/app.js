(() => {
  const state = {
    i18n: {},
    lang: "zh-TW",
    robots: { ids: [], items: [], next_id: "robot1" },
    groups: { ids: [], items: [], next_id: "group1" },
    tools: { ids: [], items: [], next_id: "tool1" },
    visions: { ids: [], items: [], next_id: "vision1" },
    weldings: { ids: [], items: [], next_id: "welding_param_1" },
    weldingStates: { ids: [], items: [], next_id: "welding_state_1" },
    robotOriginalId: "",
    groupOriginalId: "",
    toolOriginalId: "",
    visionOriginalId: "",
    weldingOriginalId: "",
    weldingStateOriginalId: "",
    robotBeforeNew: null,
    groupBeforeNew: null,
    toolBeforeNew: null,
    visionBeforeNew: null,
    weldingBeforeNew: null,
    weldingStateBeforeNew: null,
    robotIsNew: false,
    groupIsNew: false,
    toolIsNew: false,
    visionIsNew: false,
    weldingIsNew: false,
    weldingStateIsNew: false,
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
    syncVisibleButtons("vision");
    syncVisibleButtons("welding");
    syncVisibleButtons("weldingState");
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
      vision: {
        form: "#visionForm",
        card: "#visionCard",
        banner: "#visionDisabledBanner",
        save: "#visionSave",
        copy: "#visionCopy",
        isNew: () => state.visionIsNew,
      },
      welding: {
        form: "#weldingForm",
        card: "#weldingCard",
        banner: "#weldingDisabledBanner",
        save: "#weldingSave",
        copy: "#weldingCopy",
        isNew: () => state.weldingIsNew,
      },
      weldingState: {
        form: "#weldingStateForm",
        card: "#weldingStateCard",
        banner: "#weldingStateDisabledBanner",
        save: "#weldingStateSave",
        copy: "#weldingStateCopy",
        isNew: () => state.weldingStateIsNew,
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
    const forms = {
      robot: "#robotForm",
      group: "#groupForm",
      tool: "#toolForm",
      vision: "#visionForm",
      welding: "#weldingForm",
      weldingState: "#weldingStateForm",
    };
    const form = $(forms[kind]);
    if (form.elements.visible.value !== "true") {
      throw new Error(t("msg_disabled_locked"));
    }
  }

  function renderLists() {
    renderList($("#robotList"), state.robots);
    renderList($("#groupList"), state.groups);
    renderList($("#toolList"), state.tools);
    renderList($("#visionList"), state.visions);
    renderList($("#weldingList"), state.weldings);
    renderList($("#weldingStateList"), state.weldingStates);
  }

  function selVision() {
    return $("#visionList")?.value || null;
  }

  function selWelding() {
    return $("#weldingList")?.value || null;
  }

  function selWeldingState() {
    return $("#weldingStateList")?.value || null;
  }

  function currentSelections(overrides = {}) {
    return {
      robot: $("#robotList")?.value || null,
      group: $("#groupList")?.value || null,
      tool: $("#toolList")?.value || null,
      vision: selVision(),
      welding: selWelding(),
      weldingState: selWeldingState(),
      ...overrides,
    };
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

  function fillVisionForm(item) {
    const form = $("#visionForm");
    form.elements.id.value = item?.id ?? "";
    form.elements.ip.value = item?.ip ?? "";
    form.elements.product_id.value = item?.product_id ?? "";
    form.elements.product_typename.value = item?.product_typename ?? "";
    form.elements.mode.value = item?.mode ?? "";
    form.elements.original_id.value = item?.id ?? "";
    form.elements.visible.value = item ? String(!!item.visible) : "true";
    state.visionOriginalId = item?.id ?? "";
    state.visionIsNew = false;
    syncVisibleButtons("vision");
  }

  const WELDING_FIELDS = [
    "id",
    "description",
    "weld_length",
    "weld_speed",
    "safe_height",
    "executor_type",
    "yaml_rest",
  ];

  function fillWeldingForm(item) {
    const form = $("#weldingForm");
    WELDING_FIELDS.forEach((f) => {
      const val = item?.[f];
      form.elements[f].value = val === undefined || val === null ? "" : String(val);
    });
    form.elements.original_id.value = item?.id ?? "";
    form.elements.visible.value = item ? String(!!item.visible) : "true";
    state.weldingOriginalId = item?.id ?? "";
    state.weldingIsNew = false;
    syncVisibleButtons("welding");
  }

  function summaryOrNA(value) {
    if (value === undefined || value === null || value === "") return t("summary_na");
    return String(value);
  }

  function fillWeldingStateForm(item) {
    const form = $("#weldingStateForm");
    const id = item?.id ?? "";
    form.elements.id.value = id;
    form.elements.work_id.value = item?.work_id != null ? String(item.work_id) : "";
    form.elements.filename.value = item?.filename ?? (id ? `${id}.json` : "");
    form.elements.df_points.value = summaryOrNA(item?.df_points);
    form.elements.target_rt_count.value = summaryOrNA(item?.target_rt_count);
    form.elements.safe_return_rt.value = summaryOrNA(item?.safe_return_rt);
    form.elements.json_text.value = item?.json_text ?? "";
    form.elements.original_id.value = item?.id ?? "";
    form.elements.visible.value = item ? String(!!item.visible) : "true";
    state.weldingStateOriginalId = item?.id ?? "";
    state.weldingStateIsNew = false;
    syncVisibleButtons("weldingState");
  }

  function syncVisibleButtons(kind) {
    const map = {
      robot: { form: "#robotForm", text: "#robotVisibleText", btn: "#robotToggleVisible" },
      group: { form: "#groupForm", text: "#groupVisibleText", btn: "#groupToggleVisible" },
      tool: { form: "#toolForm", text: "#toolVisibleText", btn: "#toolToggleVisible" },
      vision: { form: "#visionForm", text: "#visionVisibleText", btn: "#visionToggleVisible" },
      welding: { form: "#weldingForm", text: "#weldingVisibleText", btn: "#weldingToggleVisible" },
      weldingState: {
        form: "#weldingStateForm",
        text: "#weldingStateVisibleText",
        btn: "#weldingStateToggleVisible",
      },
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

  async function reloadAll(selectOverrides = {}) {
    const select = currentSelections(selectOverrides);
    const settled = await Promise.allSettled([
      api("/api/robots"),
      api("/api/groups"),
      api("/api/tools"),
      api("/api/visions"),
      api("/api/weldings"),
      api("/api/welding-states"),
    ]);
    const errors = [];
    if (settled[0].status === "fulfilled") state.robots = settled[0].value;
    else errors.push(settled[0].reason);
    if (settled[1].status === "fulfilled") state.groups = settled[1].value;
    else errors.push(settled[1].reason);
    if (settled[2].status === "fulfilled") state.tools = settled[2].value;
    else errors.push(settled[2].reason);
    if (settled[3].status === "fulfilled") state.visions = settled[3].value;
    else errors.push(settled[3].reason);
    if (settled[4].status === "fulfilled") state.weldings = settled[4].value;
    else errors.push(settled[4].reason);
    if (settled[5].status === "fulfilled") state.weldingStates = settled[5].value;
    else errors.push(settled[5].reason);

    renderLists();

    const robots = state.robots;
    const groups = state.groups;
    const tools = state.tools;
    const visions = state.visions;
    const weldings = state.weldings;
    const weldingStates = state.weldingStates;
    const rList = $("#robotList");
    const gList = $("#groupList");
    const tList = $("#toolList");
    const vList = $("#visionList");
    const wList = $("#weldingList");
    const wsList = $("#weldingStateList");
    if (select.robot && robots.ids.includes(select.robot)) {
      rList.value = select.robot;
    }
    if (select.group && groups.ids.includes(select.group)) {
      gList.value = select.group;
    }
    if (select.tool && tools.ids.includes(select.tool)) {
      tList.value = select.tool;
    }
    if (select.vision && visions.ids.includes(select.vision)) {
      vList.value = select.vision;
    }
    if (select.welding && weldings.ids.includes(select.welding)) {
      wList.value = select.welding;
    }
    if (select.weldingState && weldingStates.ids.includes(select.weldingState)) {
      wsList.value = select.weldingState;
    }
    if (rList.value) fillRobotForm(findItem(robots, rList.value));
    else fillRobotForm(null);
    if (gList.value) fillGroupForm(findItem(groups, gList.value));
    else fillGroupForm(null);
    if (tList && tList.value) fillToolForm(findItem(tools, tList.value));
    else if (tList) fillToolForm(null);
    if (vList && vList.value) fillVisionForm(findItem(visions, vList.value));
    else if (vList) fillVisionForm(null);
    if (wList && wList.value) fillWeldingForm(findItem(weldings, wList.value));
    else if (wList) fillWeldingForm(null);
    if (wsList && wsList.value) fillWeldingStateForm(findItem(weldingStates, wsList.value));
    else if (wsList) fillWeldingStateForm(null);

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
      await reloadAll({ robot: target });
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
        await reloadAll({ robot: res.item.id });
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
        await reloadAll({ robot: res.id });
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
        await reloadAll({ robot: res.item.id });
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
      await reloadAll({ group: target });
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
        await reloadAll({ group: res.item.id });
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
        await reloadAll({ group: res.id });
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
        await reloadAll({ group: res.item.id });
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
      await reloadAll({ tool: target });
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
        await reloadAll({ tool: res.item.id });
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
        await reloadAll({ tool: res.id });
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
        await reloadAll({ tool: res.item.id });
        toast(mode === "disable" ? t("msg_soft_deleted") : t("msg_restored"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });
  }

  function bindVisionActions() {
    $("#visionList").addEventListener("change", () => {
      const item = findItem(state.visions, $("#visionList").value);
      fillVisionForm(item);
    });

    $("#visionNew").addEventListener("click", () => {
      state.visionBeforeNew = state.visionOriginalId || state.visions.ids[0] || null;
      state.visionIsNew = true;
      $("#visionList").selectedIndex = -1;
      fillVisionForm({
        id: state.visions.next_id,
        visible: true,
        mode: "",
      });
      state.visionIsNew = true;
      $("#visionForm").elements.original_id.value = "";
    });

    $("#visionCancel").addEventListener("click", async () => {
      const target = state.visionIsNew
        ? state.visionBeforeNew
        : state.visionOriginalId || state.visions.ids[0];
      state.visionIsNew = false;
      state.visionBeforeNew = null;
      await reloadAll({ vision: target });
    });

    $("#visionSave").addEventListener("click", async () => {
      try {
        assertEditable("vision");
        const form = $("#visionForm");
        const payload = {
          id: form.elements.id.value.trim(),
          original_id: form.elements.original_id.value || null,
          product_id: form.elements.product_id.value,
          product_typename: form.elements.product_typename.value,
          ip: form.elements.ip.value,
          mode: form.elements.mode.value,
          visible: form.elements.visible.value === "true",
        };
        if (!payload.id) throw new Error(t("msg_id_required"));
        const res = await api("/api/visions", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        state.visionIsNew = false;
        await reloadAll({ vision: res.item.id });
        toast(t("msg_saved"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#visionCopy").addEventListener("click", async () => {
      const id = state.visionOriginalId || $("#visionList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        assertEditable("vision");
        const res = await api(`/api/visions/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll({ vision: res.id });
        toast(t("msg_copied").replace("{id}", res.id));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#visionToggleVisible").addEventListener("click", async () => {
      const id = state.visionOriginalId || $("#visionList").value;
      if (!id || state.visionIsNew) return toast(t("msg_select_first"), true);
      const mode = $("#visionToggleVisible").dataset.mode;
      if (mode === "disable") {
        if (!confirm(t("msg_confirm_soft_delete").replace("{id}", id))) return;
      }
      try {
        const path = mode === "disable" ? "disable" : "enable";
        const res = await api(`/api/visions/${encodeURIComponent(id)}/${path}`, {
          method: "POST",
        });
        await reloadAll({ vision: res.item.id });
        toast(mode === "disable" ? t("msg_soft_deleted") : t("msg_restored"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });
  }

  function formToWeldingPayload(form) {
    return {
      id: form.elements.id.value.trim(),
      original_id: form.elements.original_id.value || null,
      description: form.elements.description.value,
      weld_length: form.elements.weld_length.value,
      weld_speed: form.elements.weld_speed.value,
      safe_height: form.elements.safe_height.value,
      executor_type: form.elements.executor_type.value,
      yaml_rest: form.elements.yaml_rest.value,
      visible: form.elements.visible.value === "true",
    };
  }

  function validateWeldingNumbers(form) {
    for (const name of ["weld_length", "weld_speed", "safe_height"]) {
      const el = form.elements[name];
      if (!el) continue;
      const s = String(el.value ?? "").trim();
      if (s === "") continue;
      if (!NUM_FULL_RE.test(s) || !Number.isFinite(Number(s))) {
        throw new Error(t("msg_number_only"));
      }
    }
  }

  function bindWeldingActions() {
    $("#weldingList").addEventListener("change", () => {
      const item = findItem(state.weldings, $("#weldingList").value);
      fillWeldingForm(item);
    });

    $("#weldingNew").addEventListener("click", () => {
      state.weldingBeforeNew = state.weldingOriginalId || state.weldings.ids[0] || null;
      state.weldingIsNew = true;
      $("#weldingList").selectedIndex = -1;
      fillWeldingForm({
        id: state.weldings.next_id,
        visible: true,
        description: "",
        weld_length: 900.0,
        weld_speed: 1.5,
        safe_height: 30.0,
        executor_type: "point_pairs",
        yaml_rest: "actions_offset: [0, 0]\nactions: []\n",
      });
      state.weldingIsNew = true;
      $("#weldingForm").elements.original_id.value = "";
    });

    $("#weldingCancel").addEventListener("click", async () => {
      const target = state.weldingIsNew
        ? state.weldingBeforeNew
        : state.weldingOriginalId || state.weldings.ids[0];
      state.weldingIsNew = false;
      state.weldingBeforeNew = null;
      await reloadAll({ welding: target });
    });

    $("#weldingSave").addEventListener("click", async () => {
      try {
        assertEditable("welding");
        const form = $("#weldingForm");
        validateWeldingNumbers(form);
        const payload = formToWeldingPayload(form);
        if (!payload.id) throw new Error(t("msg_id_required"));
        const res = await api("/api/weldings", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        state.weldingIsNew = false;
        await reloadAll({ welding: res.item.id });
        toast(t("msg_saved"));
      } catch (err) {
        const msg = String(err.message || err);
        toast(/yaml|mapping|scanner|parser/i.test(msg) ? t("msg_invalid_yaml") + " " + msg : msg, true);
      }
    });

    $("#weldingCopy").addEventListener("click", async () => {
      const id = state.weldingOriginalId || $("#weldingList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        assertEditable("welding");
        const res = await api(`/api/weldings/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll({ welding: res.id });
        toast(t("msg_copied").replace("{id}", res.id));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });

    $("#weldingToggleVisible").addEventListener("click", async () => {
      const id = state.weldingOriginalId || $("#weldingList").value;
      if (!id || state.weldingIsNew) return toast(t("msg_select_first"), true);
      const mode = $("#weldingToggleVisible").dataset.mode;
      if (mode === "disable") {
        if (!confirm(t("msg_confirm_soft_delete").replace("{id}", id))) return;
      }
      try {
        const path = mode === "disable" ? "disable" : "enable";
        const res = await api(`/api/weldings/${encodeURIComponent(id)}/${path}`, {
          method: "POST",
        });
        await reloadAll({ welding: res.item.id });
        toast(mode === "disable" ? t("msg_soft_deleted") : t("msg_restored"));
      } catch (err) {
        toast(String(err.message || err), true);
      }
    });
  }

  function mapWeldingStateError(msg) {
    const text = String(msg || "");
    if (/Invalid JSON/i.test(text)) return t("msg_invalid_json");
    if (/df_dict.*length/i.test(text) || /length mismatch/i.test(text)) return t("msg_df_dict_length");
    if (/target_rt_rev_list/i.test(text)) return t("msg_target_rt_shape");
    if (/safe_return_rt/i.test(text)) return t("msg_safe_return_rt_shape");
    if (/ID required/i.test(text)) return t("msg_id_required");
    if (/ID exists/i.test(text)) return t("msg_id_exists");
    if (/welding_state_<number>/i.test(text)) return t("hint_welding_state_id");
    return text;
  }

  function defaultWeldingStateJson() {
    return `${JSON.stringify(
      {
        df_dict: { x: [], y: [], z: [], type: [], rev_idx: [] },
        target_rt_rev_list: [],
        safe_return_rt: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
      },
      null,
      4
    )}\n`;
  }

  function bindWeldingStateActions() {
    const idInput = $("#weldingStateForm").elements.id;
    idInput.addEventListener("input", () => {
      const id = idInput.value.trim();
      const m = /^welding_state_(\d+)$/.exec(id);
      $("#weldingStateForm").elements.work_id.value = m ? m[1] : "";
      $("#weldingStateForm").elements.filename.value = id ? `${id}.json` : "";
    });

    $("#weldingStateList").addEventListener("change", () => {
      const item = findItem(state.weldingStates, $("#weldingStateList").value);
      fillWeldingStateForm(item);
    });

    $("#weldingStateNew").addEventListener("click", () => {
      state.weldingStateBeforeNew =
        state.weldingStateOriginalId || state.weldingStates.ids[0] || null;
      state.weldingStateIsNew = true;
      $("#weldingStateList").selectedIndex = -1;
      const nextId = state.weldingStates.next_id;
      const m = /^welding_state_(\d+)$/.exec(nextId);
      fillWeldingStateForm({
        id: nextId,
        work_id: m ? Number(m[1]) : "",
        filename: `${nextId}.json`,
        visible: true,
        df_points: 0,
        target_rt_count: 0,
        safe_return_rt: "[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]",
        json_text: defaultWeldingStateJson(),
      });
      state.weldingStateIsNew = true;
      $("#weldingStateForm").elements.original_id.value = "";
    });

    $("#weldingStateCancel").addEventListener("click", async () => {
      const target = state.weldingStateIsNew
        ? state.weldingStateBeforeNew
        : state.weldingStateOriginalId || state.weldingStates.ids[0];
      state.weldingStateIsNew = false;
      state.weldingStateBeforeNew = null;
      await reloadAll({ weldingState: target });
    });

    $("#weldingStateSave").addEventListener("click", async () => {
      try {
        assertEditable("weldingState");
        const form = $("#weldingStateForm");
        const payload = {
          id: form.elements.id.value.trim(),
          original_id: form.elements.original_id.value || null,
          json_text: form.elements.json_text.value,
          visible: form.elements.visible.value === "true",
        };
        if (!payload.id) throw new Error(t("msg_id_required"));
        const res = await api("/api/welding-states", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        state.weldingStateIsNew = false;
        await reloadAll({ weldingState: res.item.id });
        toast(t("msg_saved"));
      } catch (err) {
        toast(mapWeldingStateError(err.message || err), true);
      }
    });

    $("#weldingStateCopy").addEventListener("click", async () => {
      const id = state.weldingStateOriginalId || $("#weldingStateList").value;
      if (!id) return toast(t("msg_select_first"), true);
      try {
        assertEditable("weldingState");
        const res = await api(`/api/welding-states/${encodeURIComponent(id)}/copy`, {
          method: "POST",
        });
        await reloadAll({ weldingState: res.id });
        toast(t("msg_copied").replace("{id}", res.id));
      } catch (err) {
        toast(mapWeldingStateError(err.message || err), true);
      }
    });

    $("#weldingStateToggleVisible").addEventListener("click", async () => {
      const id = state.weldingStateOriginalId || $("#weldingStateList").value;
      if (!id || state.weldingStateIsNew) return toast(t("msg_select_first"), true);
      const mode = $("#weldingStateToggleVisible").dataset.mode;
      if (mode === "disable") {
        if (!confirm(t("msg_confirm_soft_delete").replace("{id}", id))) return;
      }
      try {
        const path = mode === "disable" ? "disable" : "enable";
        const res = await api(`/api/welding-states/${encodeURIComponent(id)}/${path}`, {
          method: "POST",
        });
        await reloadAll({ weldingState: res.item.id });
        toast(mode === "disable" ? t("msg_soft_deleted") : t("msg_restored"));
      } catch (err) {
        toast(mapWeldingStateError(err.message || err), true);
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
    bindVisionActions();
    bindWeldingActions();
    bindWeldingStateActions();
    await reloadAll();
  }

  boot().catch((err) => toast(String(err.message || err), true));
})();
