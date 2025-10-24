export const $ = (sel, root = document) => root.querySelector(sel);
export const el = (tag, attrs = {}, html = "") =>
  Object.assign(document.createElement(tag), attrs, html ? { innerHTML: html } : {});

export const store = {
  get: (key, fallback = null) => {
    try {
      return JSON.parse(localStorage.getItem(key)) ?? fallback;
    } catch {
      return fallback;
    }
  },
  set: (key, value) => localStorage.setItem(key, JSON.stringify(value)),
};

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function updateOnline() {
  const dot = $("#online-dot");
  const label = $("#online-label");
  const ok = navigator.onLine;
  dot.style.background = ok ? "var(--success)" : "var(--danger)";
  label.textContent = ok ? "Online" : "Offline";
}

window.addEventListener("online", updateOnline);
window.addEventListener("offline", updateOnline);
