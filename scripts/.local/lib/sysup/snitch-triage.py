#!/usr/bin/env python3
"""OpenSnitch auto-triage (root service, installed by sysup _system_hardening).

Watches the OpenSnitch UI event database and, for each program seen for the first
time, writes a permanent rule by executable path:
  allow  official-repo package file, unaltered (pacman -Qkk), not a generic tool
  deny   runs from a temp/download dir, binary deleted, or unowned file in a system dir
  (none) anything else — the OpenSnitch pop-up still asks
The first connection already happened (the daemon asked before this saw it);
the rule governs every later one. Decisions are logged to LOG.
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

DB = os.environ.get("SNITCH_DB", "")
RULES = os.environ.get("SNITCH_RULES", "/etc/opensnitchd/rules")
LOG = os.environ.get("SNITCH_TRIAGE_LOG", "/var/log/snitch-triage.log")
POLL = float(os.environ.get("SNITCH_POLL", "10"))
HOME = os.environ.get("SNITCH_HOME", "")

# Generic tools malware reuses: never allowed wholesale by path.
GENERIC = re.compile(r"^(python[0-9.]*|node|nodejs|bun|deno|perl[0-9.]*|ruby[0-9.]*|php[0-9.]*|lua[0-9.]*|"
                     r"luajit|java|bash|sh|dash|zsh|fish|busybox|curl|wget|wget2|aria2c|ssh|scp|sftp|rsync|"
                     r"git|git-remote-https?|nc|ncat|netcat|socat|telnet|openssl|gpg|dirmngr|dig|host|nslookup|drill|wine.*|"
                     r"electron[0-9]*|qemu-.*|docker.*|podman|flatpak|bwrap|xdg-open|sudo|su|pkexec)$")
DENY_DIRS = ("/tmp/", "/dev/shm/", "/var/tmp/")
SYSTEM_DIRS = ("/usr/bin/", "/usr/sbin/", "/usr/lib/", "/usr/libexec/", "/bin/", "/sbin/", "/lib/", "/opt/")


def run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def classify(path):
    """→ (verdict, reason); verdict is allow, deny or ask."""
    if not path or not path.startswith("/"):
        return "ask", "no executable path"
    if path.endswith(" (deleted)"):
        return "deny", "binary deleted while running"
    if path.startswith("/tmp/.mount_"):   # AppImage: random path each run
        return "ask", "AppImage"
    downloads = os.path.join(HOME, "Downloads") + "/" if HOME else None
    if path.startswith(DENY_DIRS) or (downloads and path.startswith(downloads)):
        return "deny", "runs from a temp/download directory"
    real = os.path.realpath(path)
    if GENERIC.match(os.path.basename(real)) or GENERIC.match(os.path.basename(path)):
        return "ask", "generic tool (interpreter/downloader/shell)"
    rc, pkg = run("pacman", "-Qoq", "--", real)
    if rc != 0 or not pkg:
        if real.startswith(SYSTEM_DIRS) and not real.startswith("/opt/"):
            return "deny", "file in a system directory owned by no package"
        return "ask", "not from a package"
    pkg = pkg.splitlines()[0]
    if run("pacman", "-Qmq", "--", pkg)[0] == 0:
        return "ask", f"AUR package {pkg}"
    _, kk = run("pacman", "-Qkk", "--", pkg)
    if real in kk:
        return "deny", f"{pkg} file altered on disk (pacman -Qkk)"
    return "allow", f"repo package {pkg}, unaltered"


def rule(verdict, path, reason):
    name = f"triage-{verdict}-{re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.basename(path))[:40]}-" \
           f"{hashlib.sha256(path.encode()).hexdigest()[:8]}"
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    return name, {
        "created": stamp, "updated": stamp, "name": name,
        "description": f"snitch-triage: {reason}",
        "enabled": True, "precedence": verdict == "deny", "nolog": False,
        "action": verdict, "duration": "always",
        "operator": {"type": "simple", "operand": "process.path", "sensitive": False,
                     "data": path, "list": []},
    }


def known_paths():
    """Executable paths that already have a rule (any rule file naming process.path)."""
    paths = set()
    for f in os.listdir(RULES) if os.path.isdir(RULES) else []:
        if not f.endswith(".json"):
            continue
        try:
            op = json.load(open(os.path.join(RULES, f))).get("operator", {})
        except (OSError, ValueError):
            continue
        if op.get("operand") == "process.path":
            paths.add(op.get("data"))
    return paths


def log(msg):
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def triage_once(seen):
    """Decide every program in the DB not yet seen; returns the number of rules written."""
    if not os.path.exists(DB):
        return 0
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5)
    try:
        procs = [r[0] for r in db.execute("SELECT DISTINCT process FROM connections")]
    finally:
        db.close()
    have, written = known_paths(), 0
    for path in procs:
        if path in seen or path in have:
            continue
        seen.add(path)
        verdict, reason = classify(path)
        if verdict == "ask":
            log(f"ASK    {path}  ({reason})")
            continue
        name, body = rule(verdict, path, reason)
        with open(os.path.join(RULES, name + ".json"), "w") as f:
            json.dump(body, f, indent=4)
            f.write("\n")
        written += 1
        log(f"{verdict.upper():6} {path}  ({reason})")
    return written


def main():
    if not DB:
        sys.exit("SNITCH_DB not set")
    seen = set()
    log(f"started: db {DB}, rules {RULES}")
    while True:
        try:
            triage_once(seen)
        except sqlite3.Error as e:   # UI restarting or writing: try again next poll
            log(f"db busy: {e}")
        if os.environ.get("SNITCH_ONCE"):
            return
        time.sleep(POLL)


if __name__ == "__main__":
    main()
