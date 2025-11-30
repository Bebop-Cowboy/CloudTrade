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
export async function api(path, opts={}) {
  const base = window.API_BASE || "";
  const r = await fetch(base + path, { headers: {'Content-Type':'application/json'}, ...opts });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function polyPrev(ticker) {
  const base = window.POLY_PROXY_BASE || "/poly";
  const r = await fetch(`${base}/prev?ticker=${encodeURIComponent(ticker)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

window.addEventListener("online", updateOnline);
window.addEventListener("offline", updateOnline);
