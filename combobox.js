// Accessible autocomplete dropdown that replaces <input list=...> / <datalist>.
// Browsers draw (or hide) the datalist arrow however they like; this one always shows
// its own arrow button, works on touch devices, and filters as you type.
function createCombobox({ input, toggle, list, getOptions, isUsed = () => false, emptyText = "No matches" }) {
  let items = [], active = -1;
  const norm = s => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  const isOpen = () => !list.hidden;

  function close() {
    list.hidden = true; active = -1;
    input.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  function setActive(i) {
    const lis = list.children;
    if (active >= 0 && lis[active]) lis[active].classList.remove("active");
    active = i;
    if (i >= 0 && lis[i]) {
      lis[i].classList.add("active");
      lis[i].scrollIntoView({ block: "nearest" });
      input.setAttribute("aria-activedescendant", lis[i].id);
    } else input.removeAttribute("aria-activedescendant");
  }

  function pick(name) {
    input.value = name;
    close();
    input.focus();
  }

  function render(filter) {
    const q = norm(filter.trim());
    const all = getOptions().slice().sort((a, b) => a.localeCompare(b));
    const starts = all.filter(n => norm(n).startsWith(q));
    const rest = all.filter(n => !norm(n).startsWith(q) && norm(n).includes(q));
    items = q ? starts.concat(rest) : all;
    list.innerHTML = "";
    if (!items.length) {
      const li = document.createElement("li");
      li.className = "combo-empty"; li.textContent = emptyText;
      li.setAttribute("aria-disabled", "true");
      list.appendChild(li);
    }
    items.forEach((name, i) => {
      const li = document.createElement("li");
      li.id = list.id + "-opt-" + i;
      li.setAttribute("role", "option");
      li.textContent = name;
      if (isUsed(name)) li.classList.add("used");
      li.addEventListener("mousedown", e => { e.preventDefault(); pick(name); });
      list.appendChild(li);
    });
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    toggle.setAttribute("aria-expanded", "true");
    active = -1;
  }

  input.addEventListener("input", () => render(input.value));
  toggle.addEventListener("mousedown", e => e.preventDefault());   // keep focus in the input
  toggle.addEventListener("click", () => {
    if (isOpen()) close(); else { render(""); input.focus(); }
  });
  input.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen()) render(input.value);
      setActive(Math.min(active + 1, items.length - 1));
    } else if (e.key === "ArrowUp" && isOpen()) {
      e.preventDefault(); setActive(Math.max(active - 1, 0));
    } else if (e.key === "Enter" && isOpen() && active >= 0) {
      e.preventDefault(); pick(items[active]);
    } else if (e.key === "Escape" && isOpen()) {
      e.preventDefault(); close();
    } else if (e.key === "Tab") close();
  });
  document.addEventListener("mousedown", e => {
    if (!list.contains(e.target) && e.target !== input && !toggle.contains(e.target)) close();
  });
  return { close };
}
