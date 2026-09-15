const state = {
    user: null,
    week: 1,
    group: "",
    search: "",
    groups: [],
    teachers: [],
    subjects: [],
    classrooms: [],
    lessons: [],
};

const days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];
const times = ["08:30–10:00", "10:10–11:40", "12:00–13:30", "13:40–15:10", "15:20–16:50", "17:00–18:30"];
const $ = (selector) => document.querySelector(selector);

async function api(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        ...options,
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) throw new Error(data.error || "Ошибка запроса.");
    return data;
}

function toast(message, type = "success") {
    const node = document.createElement("div");
    node.className = `toast ${type}`;
    node.textContent = message;
    $("#toast-container").append(node);
    setTimeout(() => node.remove(), 3200);
}

function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[char]);
}

function isAdmin() {
    return state.user?.role === "admin";
}

function roleTitle(role) {
    return { admin: "Администратор", teacher: "Преподаватель" }[role] || role;
}

async function login(event) {
    event.preventDefault();
    const username = $("#login-username").value.trim();
    const password = $("#login-password").value;

    if (!username || !password.trim()) {
        toast("Логин и пароль не могут быть пустыми.", "error");
        return;
    }

    try {
        state.user = await api("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ username, password }),
        });
        showApp();
        await loadData();
        toast("Вход выполнен.");
    } catch (error) {
        toast(error.message, "error");
    }
}

async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    state.user = null;
    $("#app-shell").classList.add("hidden");
    $("#login-screen").classList.remove("hidden");
}

function showApp() {
    $("#login-screen").classList.add("hidden");
    $("#app-shell").classList.remove("hidden");
    $("#user-name").textContent = state.user.username;
    $("#user-role").textContent = roleTitle(state.user.role);
    document.querySelectorAll(".admin-only").forEach((node) => node.classList.toggle("hidden", !isAdmin()));
}

async function loadData() {
    const data = await api("/api/bootstrap");
    Object.assign(state, data);
    await loadLessons();
    render();
}

async function loadLessons() {
    const params = new URLSearchParams({ week: state.week });
    if (state.group) params.set("group_id", state.group);
    state.lessons = await api(`/api/lessons?${params}`);
}

function render() {
    renderFilters();
    renderSchedule();
    renderDirectories();
    $("#stat-lessons").textContent = state.lessons.length;
    $("#stat-groups").textContent = state.groups.length;
    $("#stat-teachers").textContent = state.teachers.length;
}

function renderFilters() {
    $("#group-filter").innerHTML = `<option value="">Все группы</option>${state.groups.map((x) => `<option value="${x.id}">${esc(x.name)}</option>`).join("")}`;
    $("#group-filter").value = state.group;
}

function renderSchedule() {
    const body = $("#schedule-body");
    body.innerHTML = "";

    for (let weekday = 1; weekday <= 6; weekday++) {
        const row = document.createElement("div");
        row.className = "schedule-row";

        const dayCell = document.createElement("div");
        dayCell.className = "day-cell";
        dayCell.innerHTML = `<b>${days[weekday - 1]}</b>`;
        row.append(dayCell);

        for (let period = 1; period <= 6; period++) {
            const cell = document.createElement("div");
            cell.className = "schedule-cell";
            cell.dataset.weekday = weekday;
            cell.dataset.period = period;

            cell.addEventListener("dragover", (event) => {
                event.preventDefault();
                cell.classList.add("drag-over");
            });

            cell.addEventListener("dragleave", () => {
                cell.classList.remove("drag-over");
            });

            cell.addEventListener("drop", async (event) => {
                event.preventDefault();
                cell.classList.remove("drag-over");
                const id = Number(event.dataTransfer.getData("lesson-id"));
                if (id) await moveLesson(id, weekday, period);
            });

            cell.addEventListener("dblclick", () => {
                openLesson({ week: state.week, weekday, period });
            });

            row.append(cell);
        }

        body.append(row);
    }

    const query = state.search.toLowerCase().trim();
    const filteredLessons = state.lessons.filter((lesson) => {
        if (!query) return true;

        return [
            lesson.subject_name,
            lesson.group_name,
            lesson.teacher_name,
            lesson.classroom_name,
        ]
            .join(" ")
            .toLowerCase()
            .includes(query);
    });

    filteredLessons.forEach((lesson) => {
        const cell = document.querySelector(
            `.schedule-cell[data-weekday="${lesson.weekday}"][data-period="${lesson.period}"]`,
        );

        if (cell) cell.append(createCard(lesson));
    });
}

function createCard(lesson) {
    const card = document.createElement("article");
    card.className = "lesson-card";
    card.draggable = true;
    card.style.setProperty("--lesson-color", lesson.subject_color || "#6366f1");
    card.innerHTML = `<button class="card-delete" title="Удалить">×</button><b>${esc(lesson.subject_name)}</b><span>${esc(lesson.group_name)}</span><small>${esc(lesson.teacher_short)} · ауд. ${esc(lesson.classroom_name || "—")}</small>`;
    card.addEventListener("dragstart", (event) => event.dataTransfer.setData("lesson-id", lesson.id));
    card.addEventListener("dblclick", (event) => { event.stopPropagation(); openLesson(lesson); });
    card.querySelector(".card-delete").addEventListener("click", async (event) => {
        event.stopPropagation();
        if (!confirm("Удалить занятие?")) return;
        await api(`/api/lessons/${lesson.id}`, { method: "DELETE" });
        toast("Занятие удалено.");
        await loadLessons();
        render();
    });
    return card;
}

async function moveLesson(id, weekday, period) {
    const lesson = state.lessons.find((x) => x.id === id);
    if (!lesson) return;
    try {
        await api(`/api/lessons/${id}`, { method: "PUT", body: JSON.stringify({ ...lesson, weekday, period }) });
        toast("Занятие перемещено.");
        await loadLessons();
        render();
    } catch (error) {
        toast(error.message, "error");
    }
}

function fillSelect(id, items, label) {
    $(id).innerHTML = items.map((item) => `<option value="${item.id}">${esc(item[label])}</option>`).join("");
}

function openLesson(lesson = {}) {
    $("#lesson-form").reset();
    $("#lesson-id").value = lesson.id || "";
    $("#lesson-dialog-title").textContent = lesson.id ? "Редактировать занятие" : "Новое занятие";
    $("#lesson-week").value = lesson.week || state.week;
    $("#lesson-day").value = lesson.weekday || 1;
    $("#lesson-period").value = lesson.period || 1;
    fillSelect("#lesson-group", state.groups, "name");
    fillSelect("#lesson-subject", state.subjects, "name");
    fillSelect("#lesson-teacher", state.teachers, "full_name");
    $("#lesson-classroom").innerHTML = `<option value="">Без аудитории</option>${state.classrooms.map((x) => `<option value="${x.id}">${esc(x.name)}</option>`).join("")}`;
    $("#lesson-group").value = lesson.group_id || state.groups[0]?.id || "";
    $("#lesson-subject").value = lesson.subject_id || state.subjects[0]?.id || "";
    $("#lesson-teacher").value = lesson.teacher_id || state.teachers[0]?.id || "";
    $("#lesson-classroom").value = lesson.classroom_id || "";
    $("#lesson-type").value = lesson.lesson_type || "Лекция";
    $("#lesson-note").value = lesson.note || "";
    $("#delete-lesson-button").classList.toggle("hidden", !lesson.id);
    $("#lesson-dialog").showModal();
}

async function saveLesson(event) {
    event.preventDefault();

    const id = $("#lesson-id").value;
    const data = {
        week: Number($("#lesson-week").value),
        weekday: Number($("#lesson-day").value),
        period: Number($("#lesson-period").value),
        group_id: Number($("#lesson-group").value),
        subject_id: Number($("#lesson-subject").value),
        teacher_id: Number($("#lesson-teacher").value),
        classroom_id: $("#lesson-classroom").value
            ? Number($("#lesson-classroom").value)
            : null,
        lesson_type: $("#lesson-type").value.trim(),
        note: $("#lesson-note").value.trim(),
    };

    if (!data.group_id || !data.subject_id || !data.teacher_id) {
        toast("Выберите группу, дисциплину и преподавателя.", "error");
        return;
    }

    if (!data.lesson_type) {
        toast("Укажите тип занятия.", "error");
        return;
    }

    try {
        await api(
            id ? `/api/lessons/${id}` : "/api/lessons",
            {
                method: id ? "PUT" : "POST",
                body: JSON.stringify(data),
            },
        );

        $("#lesson-dialog").close();
        state.week = data.week;
        document
            .querySelectorAll(".week-button")
            .forEach((button) => {
                button.classList.toggle(
                    "active",
                    Number(button.dataset.week) === state.week,
                );
            });

        toast(id ? "Занятие обновлено." : "Занятие добавлено.");
        await loadLessons();
        render();
    } catch (error) {
        toast(error.message, "error");
    }
}

async function deleteCurrentLesson() {
    const id = Number($("#lesson-id").value);
    if (!id || !confirm("Удалить занятие?")) return;
    await api(`/api/lessons/${id}`, { method: "DELETE" });
    $("#lesson-dialog").close();
    toast("Занятие удалено.");
    await loadLessons();
    render();
}

function renderDirectories() {
    renderDirectory("#groups-list", state.groups, "groups", (x) => [x.name]);
    renderDirectory("#teachers-list", state.teachers, "teachers", (x) => [x.full_name, x.short_name]);
    renderDirectory("#subjects-list", state.subjects, "subjects", (x) => [x.name, "Дисциплина"]);
    renderDirectory("#classrooms-list", state.classrooms, "classrooms", (x) => [`Аудитория ${x.name}`]);
}

function renderDirectory(selector, items, type, text) {
    $(selector).innerHTML = items.map((item) => `<div class="directory-item"><div><b>${esc(text(item)[0])}</b><small>${esc(text(item)[1] || "")}</small></div><button data-delete="${type}" data-id="${item.id}">×</button></div>`).join("") || `<div class="empty">Нет записей</div>`;
    $(selector).querySelectorAll("[data-delete]").forEach((button) => button.addEventListener("click", async () => {
        if (!confirm("Удалить запись?")) return;
        try {
            await api(`/api/${button.dataset.delete}/${button.dataset.id}`, { method: "DELETE" });
            toast("Запись удалена.");
            await loadData();
        } catch (error) { toast(error.message, "error"); }
    }));
}

function openDirectory(type) {
    const titles = { groups: "Новая учебная группа", teachers: "Новый преподаватель", subjects: "Новая дисциплина", classrooms: "Новая аудитория" };
    $("#directory-type").value = type;
    $("#directory-title").textContent = titles[type];
    const fields = $("#directory-fields");
    if (type === "teachers") fields.innerHTML = `<div class="form-grid"><label>ФИО<input id="ref-full" required></label><label>Короткое имя<input id="ref-short" required></label><label>Цвет<input id="ref-color" type="color" value="#4f46e5"></label></div>`;
    else if (type === "subjects") fields.innerHTML = `<div class="form-grid"><label>Название<input id="ref-name" required></label><label>Цвет<input id="ref-color" type="color" value="#6366f1"></label></div>`;
    else fields.innerHTML = `<label>${type === "groups" ? "Название группы" : "Номер аудитории"}<input id="ref-name" required></label>`;
    $("#directory-dialog").showModal();
}

async function saveDirectory(event) {
    event.preventDefault();

    const type = $("#directory-type").value;
    const data = type === "teachers"
        ? {
            full_name: $("#ref-full").value.trim(),
            short_name: $("#ref-short").value.trim(),
            color: $("#ref-color").value,
        }
        : {
            name: $("#ref-name").value.trim(),
            color: $("#ref-color")?.value,
        };

    const empty = type === "teachers"
        ? !data.full_name || !data.short_name
        : !data.name;

    if (empty) {
        toast("Заполните обязательные поля.", "error");
        return;
    }

    try {
        await api(`/api/${type}`, {
            method: "POST",
            body: JSON.stringify(data),
        });
        $("#directory-dialog").close();
        toast("Запись добавлена.");
        await loadData();
    } catch (error) {
        toast(error.message, "error");
    }
}

function setup() {
    $("#login-form").addEventListener("submit", login);
    $("#logout-button").addEventListener("click", logout);
    $("#add-lesson-button").addEventListener("click", () => openLesson());
    $("#lesson-form").addEventListener("submit", saveLesson);
    $("#delete-lesson-button").addEventListener("click", deleteCurrentLesson);
    $("#group-filter").addEventListener("change", async (event) => { state.group = event.target.value; await loadLessons(); render(); });
    $("#search-input").addEventListener("input", (event) => { state.search = event.target.value; renderSchedule(); });
    $("#theme-button").addEventListener("click", () => { document.body.classList.toggle("dark"); localStorage.setItem("theme", document.body.classList.contains("dark") ? "dark" : "light"); });
    document.querySelectorAll(".week-button").forEach((button) => button.addEventListener("click", async () => { state.week = Number(button.dataset.week); document.querySelectorAll(".week-button").forEach((x) => x.classList.toggle("active", x === button)); await loadLessons(); render(); }));
    document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => button.closest("dialog").close()));
    document.querySelectorAll("[data-add]").forEach((button) => button.addEventListener("click", () => openDirectory(button.dataset.add)));
    $("#directory-form").addEventListener("submit", saveDirectory);
    document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => { if (tab.dataset.view === "directories" && !isAdmin()) return; document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x === tab)); $("#schedule-view").classList.toggle("hidden", tab.dataset.view !== "schedule"); $("#directories-view").classList.toggle("hidden", tab.dataset.view !== "directories"); }));
    if (localStorage.getItem("theme") === "dark") document.body.classList.add("dark");
}

async function start() {
    setup();
    try {
        const me = await api("/api/auth/me");
        if (me.authenticated) { state.user = me; showApp(); await loadData(); }
    } catch (_) {}
}

document.addEventListener("DOMContentLoaded", start);
