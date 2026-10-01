"""Point bcsfe-web/requirements.txt at BCSFE's newest commit, if there is one.

Run by .github/workflows/update-bcsfe.yml. Writes `changed`, `old` and `new` to $GITHUB_OUTPUT.
Only moves forward: a commit that doesn't come after the current one is ignored.
"""
import json
import os
import re
import subprocess
import urllib.request

REQUIREMENTS = "bcsfe-web/requirements.txt"
MIRROR = "fieryhenry/BCSFE-Python"
PIN = re.compile(r"BCSFE-Python/archive/([0-9a-f]{40})\.zip")


def output(**values: str) -> None:
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as fh:
        for key, value in values.items():
            fh.write(f"{key}={value}\n")
    print(values)


def newest_commit() -> str:
    out = subprocess.run(["git", "ls-remote", f"https://github.com/{MIRROR}", "HEAD"],
                         capture_output=True, text=True, check=True).stdout
    return out.split()[0]


def comes_after(old: str, new: str) -> bool:
    req = urllib.request.Request(f"https://api.github.com/repos/{MIRROR}/compare/{old}...{new}",
                                 headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["status"] == "ahead"


def main() -> None:
    text = open(REQUIREMENTS).read()
    old = PIN.search(text).group(1)
    new = newest_commit()
    if new == old or not comes_after(old, new):
        output(changed="false", old=old, new=new)
        return
    text = text.replace(old, new)
    text = re.sub(r"^# BCSFE.*$", "# BCSFE's latest code, pinned to an exact commit (kept up to date by .github/workflows/update-bcsfe.yml).",
                  text, count=1, flags=re.M)
    open(REQUIREMENTS, "w").write(text)
    output(changed="true", old=old, new=new)


if __name__ == "__main__":
    main()
