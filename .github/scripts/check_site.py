"""Quick test that the site still works with the installed BCSFE.

Run by .github/workflows/update-bcsfe.yml before a new BCSFE version goes live. For each
country it builds a save, edits it the way the site does and checks the edited save
reads back exactly. Exits non-zero on any problem.
"""
import base64
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bcsfe-web"))
os.environ.setdefault("BCSFE_DATA_DIR", tempfile.mkdtemp())

import app  # noqa: E402,F401  (the site itself must still start)
import worker  # noqa: E402
from bcsfe import core  # noqa: E402

GAME_VERSION = 150600
EDITS = {"catfood": 100, "xp": 5000, "np": 50, "normal_tickets": 10, "unlock_cats": True}
say = worker._REAL_STDOUT.write


def blank_save(cc: str) -> bytes:
    save = core.SaveFile(cc=core.CountryCode.from_code(cc), load=False, gv=core.GameVersion(GAME_VERSION))
    save.cats.cats = [core.Cat.init(i) for i in range(850)]
    save.menu_unlocks = [0] * 20
    save.unlock_popups_0 = [0] * 20
    raw = save.to_data().to_bytes()
    if core.SaveFile(core.Data(raw)).to_data().to_bytes() != raw:
        raise AssertionError("a new save doesn't read back exactly")
    return raw


def main() -> int:
    data_dir = os.environ["BCSFE_DATA_DIR"]
    worker.migrate_data(data_dir)
    core.core_data.init_data()
    problems = []
    for cc in ("en", "jp", "kr", "tw"):
        try:
            raw = blank_save(cc)
            result = worker.run({"mode": "file", "cc": cc, "data_dir": data_dir, "job_dir": tempfile.mkdtemp(),
                                 "edits": EDITS, "file_b64": base64.b64encode(raw).decode()})
            if not result.get("ok") or result.get("failed"):
                raise AssertionError(result.get("error") or result.get("failed"))
            edited = base64.b64decode(result["edited_b64"])
            save = core.SaveFile(core.Data(edited))
            if save.to_data().to_bytes() != edited or save.catfood != EDITS["catfood"]:
                raise AssertionError("the edited save doesn't read back correctly")
            say(f"{cc}: ok ({len(result['done'])} edits)\n")
        except Exception as e:  # report every country, then fail
            problems.append(f"{cc}: {type(e).__name__}: {e}")
            say(f"{cc}: FAILED {problems[-1]}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
