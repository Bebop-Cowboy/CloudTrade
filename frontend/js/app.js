import { $, el, store, updateOnline } from "./utils.js";
import { polyPrev } from "./utils.js";


const routes = {};
function route(path, view) { routes[path] = view; }

async function render() {
  const hash = location.hash.replace("#", "") || "/login";
  const view = routes[hash] || routes["/login"];
  const mount = $("#view");
  mount.innerHTML = "";
  mount.appendChild(await view());
}
window.addEventListener("hashchange", render);
window.addEventListener("load", render);

function dashboardShell(content) {
  const wrap = el("div", { className: "col-12" });
  wrap.innerHTML = `
    <div class="dash">
      <aside class="side">
        <nav class="sidebar">
          <a class="navlink" href="#/summary">Summary</a>
          <a class="navlink" href="#/news">News</a>
          <a class="navlink" href="#/trade">Trade</a>
          <a class="navlink" href="#/profile">Profile</a>
          <a class="navlink" href="#/settings">Settings</a>
        </nav>
      </aside>
      <section>${content}</section>
    </div>`;
  return wrap;
}

route("/login", async () => {
  const card = `
    <div class="col-12 col-9">
      <div class="card">
        <h1>Welcome back</h1>
        <label for="login-user">Username</label>
        <input id="login-user" />
        <label for="login-pass">Password</label>
        <input id="login-pass" type="password" />
        <div class="row" style="margin-top:12px">
          <button class="btn primary" id="login-btn">Sign In</button>
        </div>
      </div>
    </div>`;
  const wrap = el("div", { className: "col-12" }, card);
  wrap.querySelector("#login-btn").addEventListener("click", () => {
    location.hash = "/summary";
  });
  return wrap;
});

(function () {
  document.getElementById("year").textContent = new Date().getFullYear();
  updateOnline();
  if (!location.hash) location.hash = "/login";
})();

async function loadSummary() {
  try {
    const data = await polyPrev("AAPL");
    const r = data.results?.[0];
    document.querySelector("#summary").innerHTML = r
      ? `<div class="card">
           <h3>${data.ticker || "AAPL"}</h3>
           <p>O:${r.o} H:${r.h} L:${r.l} C:${r.c} Vol:${r.v}</p>
           <small>${new Date(r.t).toLocaleString()}</small>
         </div>`
      : "<em>No data</em>";
  } catch (e) {
    document.querySelector("#summary").textContent = e.message;
  }
}