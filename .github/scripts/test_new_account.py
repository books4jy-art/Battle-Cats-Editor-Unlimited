"""Make test accounts like the site's New account tab and check them the way the game does
(run by .github/workflows/test-new-account.yml; results go to the log).

For each variant: create the account with the site's own code, receive it with the transfer codes
(like the game's "Resume data transfer"), log in to the game servers with the account's password,
ask for a save key and sync the managed items, then upload it again so the log ends with fresh codes
you can enter in the game to try that variant."""
import base64
import os
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bcsfe-web"))
os.environ.setdefault("BCSFE_DATA_DIR", tempfile.mkdtemp())

import worker  # noqa: E402
from bcsfe import core  # noqa: E402

say = lambda *a: worker._REAL_STDOUT.write(" ".join(str(x) for x in a) + "\n")  # noqa: E731

VARIANTS = {
    "blank": (None, {}),
    "rookie": ("starter", {}),
    "mythic": ("ultimate", {}),
    "mythic+limited": ("ultimate", {"add_limited_cats": True}),
    "mythic+limited+dummy": ("ultimate", {"add_limited_cats": True, "add_dummy_cats": True}),
    # Battle Cats Unlimited: everything far past the game's limits
    "unlimited": ("ultimate", {"catfood": 2_147_483_647, "xp": 2_147_483_647, "rare_tickets": 2_147_483_647,
                               "platinum_tickets": 2_147_483_647, "legend_tickets": 2_147_483_647, "leadership": 32_767,
                               "upgrade": {"target": "all", "base": 999, "plus": 9999}}),
}


def check(name: str, preset: str, edits: dict, cc: str, data_dir: str) -> None:
    say(f"\n===== {name} ({cc})")
    core.core_data.game_data_getter = None
    job_dir = tempfile.mkdtemp()
    try:
        steps(preset, edits, cc, data_dir, job_dir)
    finally:
        log = os.path.join(job_dir, "bcsfe.log")
        if os.path.exists(log) and os.path.getsize(log):
            say("  game server errors logged:\n" + open(log, encoding="utf-8", errors="replace").read()[-3000:])


def steps(preset: str, edits: dict, cc: str, data_dir: str, job_dir: str) -> None:
    result = worker.run({"mode": "new", "cc": cc, "preset": preset, "edits": dict(edits),
                         "data_dir": data_dir, "job_dir": job_dir})
    say("site result: ok =", result.get("ok"), result.get("error") or "")
    for line in result.get("failed") or []:
        say("  ✗", line)
    if not result.get("transfer_code"):
        return
    made = core.SaveFile(core.Data(base64.b64decode(result["edited_b64"])), cc=core.CountryCode.from_code(cc))
    say(f"  made: game version {made.game_version.to_string()}, inquiry {made.inquiry_code}, "
        f"refresh token set: {bool(made.password_refresh_token) and 'EXPECT' not in made.password_refresh_token}, "
        f"cats unlocked {sum(1 for c in made.cats.cats if c.unlocked)}/{len(made.cats.cats)}, "
        f"catfood {made.catfood}, rare {made.rare_tickets}, plat {made.platinum_tickets}, legend {made.legend_tickets}")

    handler, req = core.ServerHandler.from_codes(result["transfer_code"], result["confirmation_code"],
                                                 core.CountryCode.from_code(cc), made.game_version,
                                                 print=False, save_backup=False)
    if handler is None:
        body = req.response.text[:300] if req is not None and req.response is not None else "no response"
        say("  ✗ receiving it with its transfer codes FAILED:", body)
        return
    got = handler.save_file
    def levels(sv):
        owned = [c for c in sv.cats.cats if c.unlocked][:400]
        top = max(owned, key=lambda c: c.upgrade.get_base() + c.upgrade.plus, default=None)
        return f"highest level {top.upgrade.get_base()}+{top.upgrade.plus} (cat {top.id})" if top else "no cats"
    say("  levels as made:", levels(made), "| after the server round trip:", levels(got))
    say(f"  ✓ received with the codes: inquiry {got.inquiry_code} (same: {got.inquiry_code == made.inquiry_code}), "
        f"password header: {handler.get_stored_password() is not None}")
    token = handler.get_auth_token_new(handler.get_stored_password() or "")
    say("  login with the account's password (what the game does at start):", "✓ ok" if token else "✗ FAILED")
    if token is None:
        pw = handler.refresh_password()
        say("  refresh password with the refresh token:", "✓ ok" if pw else "✗ FAILED")
        token = handler.get_auth_token_new(pw) if pw else None
        say("  login after refresh:", "✓ ok" if token else "✗ FAILED")
    if token:
        say("  save key:", "✓ ok" if handler.get_save_key() else "✗ FAILED")
        say("  managed items sync:", managed_items(handler, token))
    codes = handler.get_codes()
    say("  fresh codes to try this account in the game:" if codes else "  ✗ uploading again FAILED", *(codes or ()))


def managed_items(handler, token: str) -> str:
    """The managed items call the game makes, with the server's answer shown."""
    save = handler.save_file
    data = {"catfoodAmount": save.catfood, "isPaid": True, "legendTicketAmount": save.legend_tickets,
            "nonce": core.Random.get_hex_string(32), "platinumTicketAmount": save.platinum_tickets,
            "rareTicketAmount": save.rare_tickets}
    body = core.JsonFile.from_object(data).to_data(indent=None).to_str().replace(" ", "")
    headers = core.AccountHeaders(save, body).get_headers()
    headers["authorization"] = "Bearer " + token
    resp = core.RequestHandler(f"{handler.managed_item_url}/v1/managed-items", headers, core.Data(body)).post()
    if resp is None:
        return "✗ no answer"
    ok = resp.ok and '"statusCode":1' in resp.text.replace(" ", "")
    return f"{'✓' if ok else '·'} HTTP {resp.status_code} {resp.text[:300]}"


def main() -> int:
    data_dir = os.environ["BCSFE_DATA_DIR"]
    worker.migrate_data(data_dir)
    core.core_data.init_data()
    worker.accept_backup_game_data_repo()
    cc = (os.environ.get("CC") or "kr").strip()
    wanted = [v.strip() for v in (os.environ.get("VARIANTS") or ",".join(VARIANTS)).split(",") if v.strip()]
    for name in wanted:
        try:
            check(name, *VARIANTS[name], cc, data_dir)
        except Exception:  # noqa: BLE001
            say(traceback.format_exc())
    return 0


if __name__ == "__main__":
    sys.exit(main())
