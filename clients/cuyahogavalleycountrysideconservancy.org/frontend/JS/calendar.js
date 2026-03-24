(() => {
  const DATA_URL = "assets/docs/events.json";

  function parseYMD(s) {
    const [y, m, d] = String(s).split("-").map(Number);
    return new Date(y, m - 1, d);
  }

  function formatYMD(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  function todayYMD() {
    const n = new Date();
    return formatYMD(new Date(n.getFullYear(), n.getMonth(), n.getDate()));
  }

  function monthBounds(year, monthIndex) {
    const first = `${year}-${String(monthIndex + 1).padStart(2, "0")}-01`;
    const lastD = new Date(year, monthIndex + 1, 0).getDate();
    const last = `${year}-${String(monthIndex + 1).padStart(2, "0")}-${String(lastD).padStart(2, "0")}`;
    return { first, last };
  }

  function rangeIntersectsMonth(startStr, endStr, year, monthIndex) {
    const { first, last } = monthBounds(year, monthIndex);
    return startStr <= last && endStr >= first;
  }

  function formatDisplayRange(startStr, endStr) {
    const opts = { weekday: "short", month: "short", day: "numeric", year: "numeric" };
    const a = parseYMD(startStr);
    if (startStr === endStr) {
      return a.toLocaleDateString(undefined, opts);
    }
    const b = parseYMD(endStr);
    return `${a.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${b.toLocaleDateString(undefined, opts)}`;
  }

  function expandRecurring(rules) {
    const out = [];
    if (!Array.isArray(rules)) return out;
    for (const r of rules) {
      const start = parseYMD(r.start);
      const until = parseYMD(r.until);
      const wd = Number(r.weekday);
      for (let d = new Date(start); d <= until; d.setDate(d.getDate() + 1)) {
        if (d.getDay() !== wd) continue;
        const ymd = formatYMD(d);
        out.push({
          kind: "recurring",
          instanceId: `${r.id}::${ymd}`,
          sourceId: r.id,
          title: r.title,
          time: r.time,
          category: r.category,
          location: r.location,
          summary: r.summary,
          url: r.url,
          startDate: ymd,
          endDate: ymd,
        });
      }
    }
    return out;
  }

  function normalizeDiscrete(events) {
    return events.map((e) => ({
      kind: "discrete",
      instanceId: e.id,
      sourceId: e.id,
      title: e.title,
      time: e.time,
      category: e.category,
      location: e.location,
      summary: e.summary,
      url: e.url,
      startDate: e.startDate,
      endDate: e.endDate || e.startDate,
    }));
  }

  function matchesDay(inst, ymd) {
    return inst.startDate <= ymd && inst.endDate >= ymd;
  }

  function matchesSearch(inst, q) {
    if (!q) return true;
    const hay = [inst.title, inst.summary, inst.category, inst.location].join(" ").toLowerCase();
    return hay.includes(q);
  }

  function intersectsViewMonth(inst, year, monthIndex) {
    if (inst.kind === "recurring") {
      return rangeIntersectsMonth(inst.startDate, inst.endDate, year, monthIndex);
    }
    return rangeIntersectsMonth(inst.startDate, inst.endDate, year, monthIndex);
  }

  function sortKey(inst) {
    return `${inst.startDate}\0${inst.title}`;
  }

  function buildCardMarkup(inst) {
    const when = formatDisplayRange(inst.startDate, inst.endDate);
    const meta = [inst.time, inst.category, inst.location].filter(Boolean).join(" · ");
    const safeUrl = inst.url ? String(inst.url) : "";
    const link = safeUrl
      ? `<a class="program-event-card__link" href="${escapeAttr(safeUrl)}" target="_blank" rel="noopener noreferrer">Official details</a>`
      : "";
    return `
<article class="program-event-card" data-instance-id="${escapeAttr(inst.instanceId)}">
  <p class="program-event-card__when">${escapeHtml(when)}</p>
  <h3 class="program-event-card__title">${escapeHtml(inst.title)}</h3>
  <p class="program-event-card__meta">${escapeHtml(meta)}</p>
  <p class="program-event-card__summary">${escapeHtml(inst.summary || "")}</p>
  ${link}
</article>`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  function uniqueByDayRecurring(instances) {
    const byDay = new Map();
    for (const inst of instances) {
      if (inst.kind !== "recurring") continue;
      const k = inst.startDate;
      if (!byDay.has(k)) byDay.set(k, inst);
    }
    return Array.from(byDay.values());
  }

  function buildUpcomingList(discrete, recurringExpanded, todayStr, cap) {
    const disc = discrete
      .filter((i) => i.endDate >= todayStr)
      .sort((a, b) => sortKey(a).localeCompare(sortKey(b)));
    const rec = uniqueByDayRecurring(recurringExpanded)
      .filter((i) => i.startDate >= todayStr)
      .sort((a, b) => sortKey(a).localeCompare(sortKey(b)))
      .slice(0, 8);
    const merged = [...disc, ...rec].sort((a, b) => sortKey(a).localeCompare(sortKey(b)));
    const seen = new Set();
    const deduped = [];
    for (const inst of merged) {
      const sig = `${inst.title}\0${inst.startDate}\0${inst.endDate}`;
      if (seen.has(sig)) continue;
      seen.add(sig);
      deduped.push(inst);
      if (deduped.length >= cap) break;
    }
    return deduped;
  }

  function daysWithEvents(instances, year, monthIndex) {
    const { first, last } = monthBounds(year, monthIndex);
    const set = new Set();
    for (const inst of instances) {
      if (!rangeIntersectsMonth(inst.startDate, inst.endDate, year, monthIndex)) continue;
      let d = parseYMD(inst.startDate < first ? first : inst.startDate);
      const end = parseYMD(inst.endDate > last ? last : inst.endDate);
      while (d <= end) {
        const ymd = formatYMD(d);
        if (ymd >= first && ymd <= last) set.add(ymd);
        d.setDate(d.getDate() + 1);
      }
    }
    return set;
  }

  function renderMonthGrid(container, year, monthIndex, eventDays, selectedYmd, onPick) {
    const labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const firstDow = new Date(year, monthIndex, 1).getDay();
    const numDays = new Date(year, monthIndex + 1, 0).getDate();
    const today = todayYMD();

    let html = '<div class="program-cal-grid__weekdays">';
    for (const L of labels) {
      html += `<div class="program-cal-grid__wd" aria-hidden="true">${L}</div>`;
    }
    html += "</div><div class=\"program-cal-grid__cells\">";

    for (let i = 0; i < firstDow; i += 1) {
      html += '<div class="program-cal-grid__cell program-cal-grid__cell--pad" aria-hidden="true"></div>';
    }
    for (let day = 1; day <= numDays; day += 1) {
      const ymd = `${year}-${String(monthIndex + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const has = eventDays.has(ymd);
      const isSel = selectedYmd === ymd;
      const isToday = ymd === today;
      const cls = [
        "program-cal-grid__cell",
        "program-cal-grid__cell--day",
        has ? "program-cal-grid__cell--has-events" : "",
        isSel ? "is-selected" : "",
        isToday ? "is-today" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const label = new Date(year, monthIndex, day).toLocaleDateString(undefined, {
        weekday: "long",
        month: "long",
        day: "numeric",
        year: "numeric",
      });
      html += `<button type="button" class="${cls}" data-ymd="${ymd}" aria-label="${escapeAttr(label)}${has ? ", has events" : ""}${isSel ? ", selected" : ""}" aria-pressed="${isSel}"><span class="program-cal-grid__num">${day}</span>${has ? '<span class="program-cal-grid__dot" aria-hidden="true"></span>' : ""}</button>`;
    }
    const totalCells = firstDow + numDays;
    const trailing = (7 - (totalCells % 7)) % 7;
    for (let i = 0; i < trailing; i += 1) {
      html += '<div class="program-cal-grid__cell program-cal-grid__cell--pad" aria-hidden="true"></div>';
    }
    html += "</div>";
    container.innerHTML = html;

    container.querySelectorAll("button[data-ymd]").forEach((btn) => {
      btn.addEventListener("click", () => onPick(btn.getAttribute("data-ymd")));
    });
  }

  async function init() {
    const upcomingEl = document.getElementById("program-upcoming");
    const gridEl = document.getElementById("program-calendar-grid");
    const monthLabelEl = document.getElementById("program-calendar-month-label");
    const prevBtn = document.getElementById("program-calendar-prev");
    const nextBtn = document.getElementById("program-calendar-next");
    const clearBtn = document.getElementById("program-calendar-clear");
    const searchInput = document.getElementById("program-search");
    const filteredEl = document.getElementById("program-filtered-cards");
    const hintEl = document.getElementById("program-filter-hint");

    if (!upcomingEl || !gridEl || !filteredEl) return;

    let payload;
    try {
      const res = await fetch(DATA_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(String(res.status));
      payload = await res.json();
    } catch (e) {
      upcomingEl.innerHTML = `<p class="program-calendar__error">Could not load events (${escapeHtml(e.message)}).</p>`;
      filteredEl.innerHTML = "";
      return;
    }

    const discrete = normalizeDiscrete(payload.events || []);
    const recurring = expandRecurring(payload.recurring || []);
    const all = [...discrete, ...recurring].sort((a, b) => sortKey(a).localeCompare(sortKey(b)));

    const todayStr = todayYMD();
    const upcoming = buildUpcomingList(discrete, recurring, todayStr, 24);
    upcomingEl.innerHTML = upcoming.length
      ? upcoming.map((i) => buildCardMarkup(i)).join("")
      : '<p class="program-calendar__empty">No upcoming listings in the dataset. Check back or use the official links in <a href="assets/docs/research/happennings.md">happennings.md</a>.</p>';

    const now = new Date();
    let viewYear = now.getFullYear();
    let viewMonth = now.getMonth();
    let selectedYmd = null;
    let searchQ = "";

    function filterFilteredList() {
      const q = searchQ.trim().toLowerCase();
      const hasDay = Boolean(selectedYmd);
      const hasQ = Boolean(q);

      let list = all;
      if (hasDay) {
        list = list.filter((i) => matchesDay(i, selectedYmd) && matchesSearch(i, q));
      } else if (hasQ) {
        list = list.filter((i) => matchesSearch(i, q));
      } else {
        list = all.filter((i) => intersectsViewMonth(i, viewYear, viewMonth));
      }

      list = [...list].sort((a, b) => sortKey(a).localeCompare(sortKey(b)));

      if (hintEl) {
        if (hasDay && hasQ) {
          hintEl.textContent = `Showing events on ${selectedYmd} matching “${searchQ.trim()}”.`;
        } else if (hasDay) {
          hintEl.textContent = `Showing events on ${new Date(selectedYmd + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}.`;
        } else if (hasQ) {
          hintEl.textContent = `Search across all listings for “${searchQ.trim()}”.`;
        } else {
          hintEl.textContent = `Showing everything that touches ${new Date(viewYear, viewMonth).toLocaleString(undefined, { month: "long", year: "numeric" })}. Select a day to narrow.`;
        }
      }

      filteredEl.innerHTML = list.length
        ? list.map((i) => buildCardMarkup(i)).join("")
        : '<p class="program-calendar__empty">No events match the current filter.</p>';
    }

    function refreshGrid() {
      const eventDays = daysWithEvents(all, viewYear, viewMonth);
      if (monthLabelEl) {
        monthLabelEl.textContent = new Date(viewYear, viewMonth).toLocaleString(undefined, {
          month: "long",
          year: "numeric",
        });
      }
      renderMonthGrid(gridEl, viewYear, viewMonth, eventDays, selectedYmd, (ymd) => {
        selectedYmd = selectedYmd === ymd ? null : ymd;
        filterFilteredList();
        refreshGrid();
      });
      if (clearBtn) clearBtn.disabled = !selectedYmd;
    }

    prevBtn?.addEventListener("click", () => {
      selectedYmd = null;
      viewMonth -= 1;
      if (viewMonth < 0) {
        viewMonth = 11;
        viewYear -= 1;
      }
      refreshGrid();
      filterFilteredList();
    });

    nextBtn?.addEventListener("click", () => {
      selectedYmd = null;
      viewMonth += 1;
      if (viewMonth > 11) {
        viewMonth = 0;
        viewYear += 1;
      }
      refreshGrid();
      filterFilteredList();
    });

    clearBtn?.addEventListener("click", () => {
      selectedYmd = null;
      filterFilteredList();
      refreshGrid();
    });

    let t;
    searchInput?.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => {
        searchQ = searchInput.value;
        filterFilteredList();
      }, 160);
    });

    refreshGrid();
    filterFilteredList();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
