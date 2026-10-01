"""BC Level Caps: a small local page for raising every cat's level cap in your own Battle Cats APK
with TBCML (https://codeberg.org/fieryhenry/tbcml). It only listens on 127.0.0.1 (this Mac).

Open the app, pick your APK, press "Max all level caps" (or type your own caps), and the modified
APK is saved to your Downloads folder.
"""
from __future__ import annotations

import io
import os
import re
import shutil
import socket
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from flask import Flask, jsonify, request, send_file

MAX_BASE = 9999  # the "Max" button: highest base level cap
MAX_PLUS = 9999  # and plus level cap
LIMIT = 65535  # levels are stored as 2-byte numbers in the save; never go past this

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = None  # APKs are a few hundred MB
WORK = Path(tempfile.mkdtemp(prefix="bc-level-caps-"))
STATE: dict = {"running": False, "log": [], "result": None, "error": None}
LOCK = threading.Lock()


def log(text: str) -> None:
    STATE["log"].append(f"{time.strftime('%H:%M:%S')}  {text}")


class _Tee(io.TextIOBase):
    """Send TBCML's own printed progress into the page's log (one line at a time)."""

    def __init__(self) -> None:
        self.buf = ""

    def write(self, s: str) -> int:
        self.buf += s.replace("\r", "\n")
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            line = line.strip()
            if line and not line.startswith("[#") and not line.startswith("[-"):
                log(line)
        return len(s)


def guess_version(name: str) -> tuple[str | None, str | None]:
    """'jp.co.ponos.battlecatsen_15.6.0-1506000_..._apkmirror.apkm' -> ('en', '15.6.0')."""
    m = re.search(r"battlecats(en|kr|tw)?[_-](\d+\.\d+\.\d+)", name)
    if not m:
        return None, None
    return (m.group(1) or "jp"), m.group(2)


def merge_bundle(path: Path) -> Path:
    """Split-APK bundles (.apkm from APKMirror, .xapk, .apks) are merged into one normal APK with
    APKEditor (https://github.com/REAndroid/APKEditor), so the game engine (lib/) and data are in one file."""
    import subprocess

    jar = os.environ.get("APKEDITOR_JAR", "")
    if not jar or not os.path.exists(jar):
        raise RuntimeError("APKEditor (used to merge app bundles) is missing from the app.")
    out = path.with_name(path.stem + "-merged.apk")
    cmd = ["java", "-jar", jar, "m", "-i", str(path), "-o", str(out), "-f"]
    log("Merging the bundle into one APK with APKEditor…")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    for line in (proc.stdout + proc.stderr).splitlines()[-15:]:
        if line.strip():
            log("  " + line.strip())
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError("Couldn't merge the bundle into one APK (see the lines above).")
    return out


def run_tool(cmd: list[str]) -> tuple[int, str]:
    import subprocess

    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def python_align(src: Path, dst: Path) -> None:
    """Same job as Android's zipalign -p 4: every uncompressed file starts on a 4-byte boundary
    (native .so libraries on a 4096-byte page), padded with an alignment extra field."""
    import struct
    import zipfile

    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", allowZip64=True) as zout:
        for info in zin.infolist():
            data = zin.read(info)
            new = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            new.compress_type = info.compress_type
            new.external_attr = info.external_attr
            new.create_system = info.create_system
            if info.compress_type == zipfile.ZIP_STORED:
                align = 4096 if info.filename.endswith(".so") else 4
                header = 30 + len(info.filename.encode("utf-8"))
                start = zout.fp.tell() + header + 6  # 6 = alignment field header + its 2-byte value
                pad = (-start) % align
                new.extra = struct.pack("<HHH", 0xD935, 2 + pad, align) + b"\0" * pad
            zout.writestr(new, data)


def align_apk(apk: Path) -> None:
    aligned = apk.with_name(apk.stem + "-aligned.apk")
    log("Aligning the APK (zipalign)…")
    code, out = run_tool(["zipalign", "-f", "-p", "4", str(apk), str(aligned)])
    if code != 0 or not aligned.exists():
        log("  zipalign couldn't do it: " + (out.splitlines()[-1] if out else f"exit code {code}"))
        log("  using the built-in aligner instead…")
        python_align(apk, aligned)
    shutil.move(str(aligned), str(apk))


def sign_apk(apk: Path) -> None:
    log("Signing the APK (apksigner)…")
    keystore = Path.home() / "Documents" / "tbcml" / "tbcml.keystore"
    keystore.parent.mkdir(parents=True, exist_ok=True)
    password = "TBCML_CUSTOM_APK"
    if not keystore.exists():
        code, out = run_tool(["keytool", "-genkey", "-keystore", str(keystore), "-alias", "tbcml", "-keyalg", "RSA",
                              "-keysize", "2048", "-validity", "10000", "-storepass", password, "-keypass", password,
                              "-dname", "CN=BC Level Caps"])
        if code != 0:
            raise RuntimeError("Couldn't create a signing key: " + out[-400:])
    code, out = run_tool(["apksigner", "sign", "--ks", str(keystore), "--ks-key-alias", "tbcml",
                          "--ks-pass", f"pass:{password}", "--key-pass", f"pass:{password}", str(apk)])
    if code != 0:
        raise RuntimeError("Couldn't sign the APK: " + out[-600:])
    code, out = run_tool(["apksigner", "verify", str(apk)])
    if code != 0:
        raise RuntimeError("The signed APK didn't pass apksigner's check: " + out[-600:])
    log("  signed and verified")


def build(apk_path: Path, base: int, plus: int, cc_fallback: str, gv_fallback: str) -> Path:
    import tbcml

    log(f"TBCML {getattr(tbcml, '__version__', '?')}: reading the APK…")
    cc_guess, gv_guess = guess_version(apk_path.name)
    if cc_guess and gv_guess:
        cc_fallback, gv_fallback = cc_guess, gv_guess
        log(f"From the file name: country {cc_fallback}, version {gv_fallback}")
    if apk_path.suffix.lower() in (".apkm", ".xapk", ".apks"):
        apk_path = merge_bundle(apk_path)
    pkg, res = tbcml.Apk.from_pkg_path(
        str(apk_path),
        cc_overwrite=tbcml.CountryCode.from_cc(cc_fallback),
        gv_overwrite=tbcml.GameVersion.from_string(gv_fallback),
        skip_signature_check=True,
    )
    if pkg is None:
        raise RuntimeError(f"Couldn't read the APK: {getattr(res, 'error', res)}")
    log(f"Game: {pkg.country_code.get_code()} version {pkg.game_version.to_string()}")

    loader = tbcml.ModLoader(pkg.country_code, pkg.game_version)
    log("Unpacking the APK and loading the game data (this takes a few minutes)…")
    # Only game data files change, so the APK is simply unzipped (no apktool / resource decoding needed).
    loader.initialize_apk(apk=pkg, skip_signature_check=True, use_apktool=False, decode_resources=False)
    packs = loader.get_game_packs()
    total = tbcml.Cat.get_total_cats(packs)
    if not total:
        raise RuntimeError("Couldn't find the character list (unitbuy.csv) in this APK.")
    log(f"Raising the level caps of all {total} characters to {base}+{plus}…")

    mod = tbcml.Mod(
        name=f"Level caps {base}+{plus}",
        authors="BC Level Caps",
        short_description=f"Every character's level cap raised to {base}+{plus}",
    )
    for cat_id in range(total):
        cat = tbcml.Cat(cat_id)
        cat.get_unitbuy().set_max_level(
            base,
            plus,
            level_until_catsye_req=base,  # level all the way without Catseyes
            original_base_max=base,
            original_plus_max=plus,
        )
        mod.add_modification(cat)

    log("Building the modified APK (this takes a few minutes)…")
    loader.apply(mod, use_apktool=False, sign=False, zip_align=False)  # aligned and signed below, with clear errors
    final = Path(pkg.final_pkg_path.to_str())
    if not final.exists():
        raise RuntimeError("TBCML finished but the modified APK wasn't created.")
    align_apk(final)
    sign_apk(final)
    downloads = Path.home() / "Downloads"
    downloads.mkdir(exist_ok=True)
    out = downloads / f"{apk_path.stem.replace('-merged', '')}-levelcaps-{base}+{plus}.apk"
    shutil.copy2(final, out)
    return out


def run_job(apk_path: Path, base: int, plus: int, cc: str, gv: str) -> None:
    tee = _Tee()
    try:
        with redirect_stdout(tee), redirect_stderr(tee):
            out = build(apk_path, base, plus, cc, gv)
        STATE["result"] = str(out)
        log(f"Done! Saved to {out}")
    except Exception as e:  # noqa: BLE001 - shown on the page
        STATE["error"] = str(e) or e.__class__.__name__
        log("Failed: " + STATE["error"])
        for line in traceback.format_exc().splitlines()[-12:]:
            log("  " + line)
    finally:
        STATE["running"] = False


@app.get("/")
def index():
    return PAGE.replace("{MAX_BASE}", str(MAX_BASE)).replace("{MAX_PLUS}", str(MAX_PLUS)).replace("{LIMIT}", str(LIMIT))


@app.post("/build")
def start_build():
    with LOCK:
        if STATE["running"]:
            return jsonify(ok=False, error="A build is already running."), 409
        upload = request.files.get("apk")
        if upload is None or not upload.filename:
            return jsonify(ok=False, error="Choose your APK file first."), 400
        try:
            base = int(request.form.get("base") or MAX_BASE)
            plus = int(request.form.get("plus") or MAX_PLUS)
        except ValueError:
            return jsonify(ok=False, error="Level caps must be whole numbers."), 400
        if not (1 <= base <= LIMIT and 0 <= plus <= LIMIT):
            return jsonify(ok=False, error=f"Level caps must be between 1 and {LIMIT:,}."), 400
        name = Path(upload.filename).name
        if not name.lower().endswith((".apk", ".xapk", ".apkm", ".apks")):
            return jsonify(ok=False, error="Choose an .apk, .apkm, .xapk or .apks file."), 400
        apk_path = WORK / name
        upload.save(apk_path)
        STATE.update(running=True, log=[], result=None, error=None)
        log(f"Got {name} ({apk_path.stat().st_size / 1e6:.0f} MB)")
        cc = (request.form.get("cc") or "en").strip().lower()
        gv = (request.form.get("gv") or "15.6.0").strip()
        threading.Thread(target=run_job, args=(apk_path, base, plus, cc, gv), daemon=True).start()
    return jsonify(ok=True)


@app.get("/status")
def status():
    return jsonify(running=STATE["running"], log=STATE["log"][-400:], result=STATE["result"], error=STATE["error"])


@app.get("/download")
def download():
    if not STATE["result"]:
        return "Nothing built yet.", 404
    return send_file(STATE["result"], as_attachment=True)


@app.post("/quit")
def quit_app():
    threading.Timer(0.3, lambda: os._exit(0)).start()
    return jsonify(ok=True)


@app.get("/health")
def health():
    return "ok"


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BC Level Caps</title>
<style>
 :root { color-scheme: dark; --bg:#0b0d12; --card:#12151c; --line:rgba(255,255,255,.1); --fg:#e5e7eb; --dim:#9ca3af; --sky:#38bdf8; --red:#f87171; }
 * { box-sizing: border-box; } body { margin:0; background:var(--bg); color:var(--fg); font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, sans-serif; }
 main { max-width: 720px; margin: 0 auto; padding: 32px 16px 60px; }
 h1 { font-size: 28px; margin: 0 0 4px; } h1 span { color: var(--sky); } p.lede { color: var(--dim); margin: 0 0 20px; }
 .card { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px; margin-bottom: 16px; }
 .warn { border-color: rgba(248,113,113,.5); background: rgba(248,113,113,.08); color: #fecaca; }
 .warn b { color: var(--red); }
 label { display:block; font-size: 13px; color: var(--dim); margin: 0 0 6px; }
 input[type=number], input[type=text] { width: 100%; background:#0b0d12; color: var(--fg); border:1px solid var(--line); border-radius:10px; padding:10px 12px; font-size:15px; }
 .row { display:flex; gap:12px; flex-wrap:wrap; } .row > div { flex:1; min-width: 140px; }
 button { border:0; border-radius:12px; padding:14px 18px; font-size:16px; font-weight:600; cursor:pointer; }
 .max { width:100%; background: var(--sky); color:#04121c; font-size:18px; padding:18px; margin-top: 4px; }
 .alt { background: rgba(255,255,255,.08); color: var(--fg); }
 button:disabled { opacity:.5; cursor:default; }
 .file { border: 2px dashed var(--line); border-radius: 14px; padding: 22px; text-align:center; cursor:pointer; }
 .file.has { border-color: var(--sky); }
 pre { background:#07090d; border:1px solid var(--line); border-radius:12px; padding:12px; max-height: 320px; overflow:auto; font-size:12px; white-space: pre-wrap; margin:0; }
 .ok { color:#86efac; } .err { color: var(--red); } details summary { cursor:pointer; color: var(--dim); }
 a.dl { display:inline-block; margin-top:12px; background:#22c55e; color:#04120a; padding:12px 16px; border-radius:12px; font-weight:700; text-decoration:none; }
</style></head><body><main>
<h1><span>BC</span> Level Caps</h1>
<p class="lede">Raise every cat's level cap in your own Battle Cats APK with TBCML. Everything happens on this Mac.</p>

<div class="card warn"><b>&#9888; Warning</b><br>
A modified game app is the easiest thing for the game to detect: use a spare account and keep your
original transfer codes. Uninstalling the store app to install this one deletes the game's local data, so make
transfer codes first. Very high levels can break stats or the level-up screen. Don't share the modified APK.</div>

<div class="card">
 <label>1. Your APK file</label>
 <div class="file" id="drop">Click to choose your Battle Cats .apk / .apkm / .xapk (or drop it here)<br><small id="fname" style="color:var(--dim)"></small></div>
 <input type="file" id="apk" accept=".apk,.apkm,.xapk,.apks" hidden>
</div>

<div class="card">
 <label>2. Level caps</label>
 <button class="max" id="maxBtn">Max all level caps ({MAX_BASE}+{MAX_PLUS})</button>
 <details style="margin-top:14px"><summary>Or set your own caps</summary>
  <div class="row" style="margin-top:10px">
   <div><label for="base">Base level cap</label><input type="number" id="base" min="1" max="{LIMIT}" value="{MAX_BASE}"></div>
   <div><label for="plus">Plus level cap</label><input type="number" id="plus" min="0" max="{LIMIT}" value="{MAX_PLUS}"></div>
  </div>
  <button class="alt" id="customBtn" style="margin-top:12px">Build with these caps</button>
 </details>
 <details style="margin-top:12px"><summary>If the version can't be read from the APK</summary>
  <div class="row" style="margin-top:10px">
   <div><label for="cc">Country</label><input type="text" id="cc" value="en"></div>
   <div><label for="gv">Game version</label><input type="text" id="gv" value="15.6.0"></div>
  </div>
 </details>
</div>

<div class="card">
 <label>3. Progress</label>
 <pre id="log">Nothing running yet.</pre>
 <div id="done"></div>
</div>
<button class="alt" id="quit">Quit BC Level Caps</button>

<script>
const $ = (id) => document.getElementById(id);
let file = null, timer = null;
const pick = (f) => { file = f; $("fname").textContent = f ? f.name + " (" + Math.round(f.size / 1e6) + " MB)" : ""; $("drop").classList.toggle("has", !!f); };
$("drop").onclick = () => $("apk").click();
$("apk").onchange = (e) => pick(e.target.files[0] || null);
$("drop").ondragover = (e) => { e.preventDefault(); };
$("drop").ondrop = (e) => { e.preventDefault(); pick(e.dataTransfer.files[0] || null); };
async function start(base, plus) {
  if (!file) { alert("Choose your APK file first."); return; }
  const fd = new FormData();
  fd.append("apk", file); fd.append("base", base); fd.append("plus", plus);
  fd.append("cc", $("cc").value); fd.append("gv", $("gv").value);
  setBusy(true); $("log").textContent = "Uploading the APK to the tool (on this Mac)…"; $("done").innerHTML = "";
  const r = await fetch("/build", { method: "POST", body: fd }).then(r => r.json()).catch(() => ({ ok: false, error: "The tool stopped. Open it again." }));
  if (!r.ok) { $("log").textContent = r.error; setBusy(false); return; }
  timer = setInterval(poll, 1500);
}
async function poll() {
  const s = await fetch("/status").then(r => r.json()).catch(() => null);
  if (!s) return;
  $("log").textContent = s.log.join("\\n"); $("log").scrollTop = 1e9;
  if (!s.running) {
    clearInterval(timer); setBusy(false);
    $("done").innerHTML = s.result ? '<p class="ok">Done! Saved to your Downloads folder:<br>' + s.result + '</p><a class="dl" href="/download">Download again</a>'
                                   : '<p class="err">Failed: ' + (s.error || "unknown error") + '</p>';
  }
}
function setBusy(b) { $("maxBtn").disabled = b; $("customBtn").disabled = b; }
$("maxBtn").onclick = () => start({MAX_BASE}, {MAX_PLUS});
$("customBtn").onclick = () => start($("base").value, $("plus").value);
$("quit").onclick = () => fetch("/quit", { method: "POST" }).finally(() => { document.body.innerHTML = "<main><h1>BC Level Caps closed</h1><p class=lede>You can close this tab.</p></main>"; });
</script></main></body></html>
"""


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    port = int(os.environ.get("BC_LEVEL_CAPS_PORT") or free_port())
    url = f"http://127.0.0.1:{port}/"
    if not os.environ.get("BC_LEVEL_CAPS_NO_BROWSER"):
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"BC Level Caps running at {url}", flush=True)
    app.run(host="127.0.0.1", port=port, threaded=True)


if __name__ == "__main__":
    sys.exit(main())
