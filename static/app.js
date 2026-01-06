let busy = false;

function fmtTemp(v){
  if (v === null || v === undefined) return "—";
  return `${Number(v).toFixed(1)} °C`;
}
function fmtHum(v){
  if (v === null || v === undefined) return "—";
  return `${Math.round(Number(v))} %`;
}
function fmtMinFromSeconds(s){
  if (s === null || s === undefined) return "—";
  const m = Number(s) / 60;
  return `${m.toFixed(1)} min`;
}
function pct(v){
  if (v === null || v === undefined) return null;
  const n = Math.max(0, Math.min(100, Number(v)));
  return n;
}
function setFill(el, value){
  const n = pct(value);
  el.style.width = (n === null ? "0%" : `${n}%`);
  el.classList.toggle("warn", n !== null && n >= 85);
}
function nowTime(){
  const d = new Date();
  return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}

async function postJSON(url, body){
  busy = true;
  setButtonsDisabled(true);
  try{
    const res = await fetch(url, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(body || {})
    });
    return await res.json().catch(()=> ({}));
  } finally {
    busy = false;
    setButtonsDisabled(false);
  }
}

function setButtonsDisabled(disabled){
  for (const id of ["btnAuto","btnOn","btnOff","btnReboot"]){
    const el = document.getElementById(id);
    if (el) el.disabled = disabled;
  }
}

function toast(msg){
  const el = document.getElementById("toast");
  if (!el) return;
  el.style.display = "block";
  el.innerText = msg;
  setTimeout(()=>{ el.style.display = "none"; }, 4000);
}

function normalizeRelay(r){
  if (typeof r === "boolean"){
    return { state: r ? "ON" : "OFF", mode: "—", manual: "—" };
  }
  if (r && typeof r === "object"){
    const state = r.state ?? "—";
    const mode = r.mode ?? "—";
    const manual = r.manual ?? "—";
    return { state, mode, manual };
  }
  return { state: "—", mode: "—", manual: "—" };
}

function secsAgo(ts){
  if (!ts) return null;
  const now = Math.floor(Date.now()/1000);
  return now - ts;
}

async function refresh(){
  try{
    const res = await fetch("/api/status", { cache: "no-store" });
    const data = await res.json();

    // connexion badge
    document.getElementById("pillText").innerText = "Connecté";
    document.getElementById("dot").style.background = "var(--good)";
    document.getElementById("dot").style.boxShadow = "0 0 0 4px rgba(52,211,153,.12)";
    document.getElementById("apiHint").innerText = "";

    // relais
    const rr = normalizeRelay(data.relay);
    document.getElementById("relayState").innerText = rr.state;
    document.getElementById("relayMode").innerText = rr.mode;
    document.getElementById("relayManual").innerText = rr.manual;
    document.getElementById("lastUpdate").innerText = nowTime();

    const badge = document.getElementById("relayBadge");
    const isOn = (rr.state === "ON");
    badge.classList.toggle("on", isOn);
    badge.classList.toggle("off", !isOn);

    // DHT
    const dht = data.dht || {};
    document.getElementById("dhtTemp").innerText = fmtTemp(dht.temp);
    document.getElementById("dhtHum").innerText = fmtHum(dht.hum);
    const age = secsAgo(dht.ts);
    document.getElementById("dhtAge").innerText =
      (age === null) ? "—" : `Mis à jour il y a ${age}s`;

    // telemetry
    const t = data.telemetry || {};
    document.getElementById("cpuTemp").innerText = fmtTemp(t.temp_cpu);

    document.getElementById("cpuPctLabel").innerText = (pct(t.cpu) ?? "—") + (pct(t.cpu) !== null ? "%" : "");
    document.getElementById("ramPctLabel").innerText = (pct(t.ram) ?? "—") + (pct(t.ram) !== null ? "%" : "");
    document.getElementById("diskPctLabel").innerText = (pct(t.disk) ?? "—") + (pct(t.disk) !== null ? "%" : "");

    setFill(document.getElementById("cpuFill"), t.cpu);
    setFill(document.getElementById("ramFill"), t.ram);
    setFill(document.getElementById("diskFill"), t.disk);

    // daily stats
    if (data.daily && data.today){
      document.getElementById("txDay").innerText = data.today;
      document.getElementById("txCount").innerText = data.daily.n_tx ?? "—";
      document.getElementById("txTotal").innerText = fmtMinFromSeconds(data.daily.total_s);
      document.getElementById("txMax").innerText = (data.daily.max_s ?? "—") + ((data.daily.max_s !== undefined) ? " s" : "");
    }

    // FFVL / balisemeteo
    const ff = data.ffvl || {};
    if (ff.ok) {
      const avg = (ff.wind_avg_kmh !== null && ff.wind_avg_dir_deg !== null)
        ? `${ff.wind_avg_kmh} km/h • ${ff.wind_avg_dir_deg}°`
        : "—";
      const mx = (ff.wind_max_kmh !== null && ff.wind_max_dir_deg !== null)
        ? `${ff.wind_max_kmh} km/h • ${ff.wind_max_dir_deg}°`
        : "—";
      document.getElementById("ffvlAvg").innerText = avg;
      document.getElementById("ffvlMax").innerText = mx;
      document.getElementById("ffvlTemp").innerText =
        (ff.temp_c !== null && ff.temp_c !== undefined) ? `${Number(ff.temp_c).toFixed(1)} °C` : "—";
      document.getElementById("ffvlTime").innerText = ff.releve ? `Relevé : ${ff.releve}` : "Relevé : —";
    } else {
      document.getElementById("ffvlAvg").innerText = "—";
      document.getElementById("ffvlMax").innerText = "—";
      document.getElementById("ffvlTemp").innerText = "—";
      document.getElementById("ffvlTime").innerText = ff.error ? `Erreur météo : ${ff.error}` : "Météo : indisponible";
    }

  } catch (e){
    document.getElementById("pillText").innerText = "Erreur API";
    document.getElementById("dot").style.background = "var(--bad)";
    document.getElementById("dot").style.boxShadow = "0 0 0 4px rgba(251,113,133,.12)";
    document.getElementById("apiHint").innerText = "L’API /api/status ne répond pas. Vérifie le service svx-dashboard.";
  }
}

// actions UI
function setAuto(){
  postJSON("/api/relay/auto").then(()=>{ toast("Mode AUTO activé"); refresh(); });
}

function manualOn(){
  postJSON("/api/relay/manual", {state:"ON"}).then(()=>{ toast("MANU ON"); refresh(); });
}

function manualOff(){
  postJSON("/api/relay/manual", {state:"OFF"}).then(()=>{ toast("MANU OFF"); refresh(); });
}

async function rebootPi(){
  const ok = confirm("Redémarrer le Raspberry maintenant ?");
  if (!ok) return;
  toast("Redémarrage en cours...");
  try{
    await postJSON("/api/reboot", {});
  } catch(e){}
  // après reboot, la page va tomber. On laisse un message.
}

setInterval(refresh, 2000);
refresh();

