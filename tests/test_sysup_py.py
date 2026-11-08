"""sysup.py: config, resolution, run plan, unused report, flag commands."""
import datetime
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/.local/lib/sysup/sysup.py"
_spec = importlib.util.spec_from_file_location("sysup_helper", HELPER)
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)


def fixture_repo(root: Path) -> Path:
    """Minimal repo: two profiles, one dotset with two stow packages + profile dirs."""
    d = root / "dots"
    (d / "profiles").mkdir(parents=True)
    (d / "packages.toml").write_text(
        '[paru]\ninstall = ["fish", "git", "steam"]\nremove = ["wine"]\nhold = ["vectorcraft"]\nskip = ["git"]\n'
        '[flatpak]\ninstall = ["com.spotify.Client"]\nremove = ["org.old.App"]\n'
        '[systemd]\nenable = ["cups", "bluetooth"]\nuser = ["mpd"]\n[npm]\ninstall = ["@x/dsh"]\n[uv]\ninstall = ["graphifyy"]\n[ufw]\nallow = ["2234/tcp"]\n')
    (d / "profiles/desktop.toml").write_text(
        'description = "Tower"\nhostname = "desktop"\ndotset = "mine"\nfeatures = ["amd-gpu-tuning"]\n'
        '[paru]\ninstall = ["vulkan-radeon", "fish"]\n[systemd]\nenable = ["ollama", "cups"]\n[ufw]\nallow = ["from 192.168.1.0/24 to any port 22", "2234/tcp"]\n')
    (d / "profiles/surface.toml").write_text(
        'description = "Tablet"\nhostname = "surface"\ndotset = "mine"\nfeatures = ["linux-surface"]\n')
    (d / "projects.toml").write_text('[[repo]]\nname = "dots"\nurl = "git@x:dots.git"\n'
                                     '[[repo]]\nname = "app"\nurl = "git@x:app.git"\nbuild = "make install"\n')
    for p in ("alacritty", "fish", "desktop", "surface"):
        (d / "dotsets/mine" / p).mkdir(parents=True)
    return d

class Tmp(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="sysup-test-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.dots = fixture_repo(self.root)
        self.cfg_path = self.root / "cfg/config.toml"
        self.enterContext(patch.dict(os.environ, {"XDG_STATE_HOME": str(self.root / "state")}))

    def cli(self, *args, cfg=True, **env):
        e = {**os.environ, "SYSUP_DOTS": str(self.dots), "HOSTNAME": "desktop",
             "XDG_CONFIG_HOME": str(self.root / "xdg"), **env}
        if cfg:
            e["SYSUP_CONFIG"] = str(self.cfg_path)
        return subprocess.run([sys.executable, "-B", str(HELPER), *args], env=e, capture_output=True, text=True)


class ConfigTests(Tmp):
    def test_missing_file_gives_full_defaults(self):
        cfg = S.load_local(self.cfg_path)
        self.assertIsNone(cfg["profile"])
        self.assertEqual(cfg["paru"], {"add": [], "remove": []})
        self.assertEqual(cfg["declined"], {"paru": [], "flatpak": []})
        self.assertEqual(cfg["once"], {})
        self.assertEqual(cfg["select"], {})

    def test_partial_file_keeps_defaults_for_missing_keys(self):
        self.cfg_path.parent.mkdir()
        self.cfg_path.write_text('profile = "desktop"\n[paru]\nadd = ["obs"]\n')
        cfg = S.load_local(self.cfg_path)
        self.assertEqual(cfg["profile"], "desktop")
        self.assertEqual(cfg["paru"], {"add": ["obs"], "remove": []})
        self.assertEqual(cfg["flatpak"], {"add": [], "remove": []})

    def test_round_trip(self):
        cfg = S.load_local(self.cfg_path)
        cfg.update(profile="desktop", dotset="none")
        cfg["paru"]["add"] = ["obs-studio", 'we"ird']
        cfg["declined"]["flatpak"] = ["com.x.Y"]
        cfg["once"] = {"fish": datetime.date(2026, 10, 21), "keyring-pam": "skip"}
        cfg["select"] = {"repos": ["dots"]}
        S.save_local(cfg, self.cfg_path)
        self.assertEqual(S.load_local(self.cfg_path), cfg)

    def test_broken_toml_gives_clear_error_not_traceback(self):
        self.cfg_path.parent.mkdir()
        self.cfg_path.write_text('profile = "desktop\n')  # unterminated string
        with self.assertRaises(S.ConfigError) as ctx:
            S.load_local(self.cfg_path)
        self.assertIn(str(self.cfg_path), str(ctx.exception))
        self.assertIn("fix or delete", str(ctx.exception))

    def test_save_is_atomic_no_leftovers(self):
        S.save_local(S.load_local(self.cfg_path), self.cfg_path)
        self.assertEqual([p.name for p in self.cfg_path.parent.iterdir()], ["config.toml"])

    def test_config_path_honours_env(self):
        old = os.environ.get("SYSUP_CONFIG")
        os.environ["SYSUP_CONFIG"] = str(self.cfg_path)
        self.addCleanup(lambda: os.environ.pop("SYSUP_CONFIG") if old is None else os.environ.update(SYSUP_CONFIG=old))
        self.assertEqual(S.config_path(), self.cfg_path)

    def test_load_repo(self):
        repo = S.load_repo(self.dots)
        self.assertEqual(sorted(repo.profiles), ["desktop", "surface"])
        self.assertEqual(repo.dotsets, ["mine"])
        self.assertEqual(repo.stow_pkgs("mine"), ["alacritty", "fish"])
        self.assertEqual(repo.stow_pkgs("none"), [])
        self.assertEqual(repo.projects[0]["name"], "dots")
        self.assertEqual(repo.packages["paru"]["hold"], ["vectorcraft"])

    def test_valid_choice(self):
        repo = S.load_repo(self.dots)
        cfg = S.load_local(self.cfg_path)
        self.assertFalse(S.valid_choice(cfg, repo))
        cfg.update(profile="desktop", dotset="mine")
        self.assertTrue(S.valid_choice(cfg, repo))
        cfg["dotset"] = "none"
        self.assertTrue(S.valid_choice(cfg, repo))
        cfg["dotset"] = "deleted"
        self.assertFalse(S.valid_choice(cfg, repo))
        cfg.update(profile="gone", dotset="mine")
        self.assertFalse(S.valid_choice(cfg, repo))



class ResolveTests(Tmp):
    def setUp(self):
        super().setUp()
        self.repo = S.load_repo(self.dots)
        self.cfg = S.load_local(self.cfg_path)
        self.cfg.update(profile="desktop", dotset="mine")

    def test_repo_plus_profile_minus_skip_deduped(self):
        r = S.resolve(self.repo, self.cfg)
        self.assertEqual(r["paru_install"], ["fish", "steam", "vulkan-radeon"])
        self.assertEqual(r["paru_hold"], ["vectorcraft"])
        self.assertEqual(r["paru_skip"], ["git"])
        self.assertEqual(r["flatpak_install"], ["com.spotify.Client"])

    def test_local_add_remove_and_declined(self):
        self.cfg["paru"] = {"add": ["obs"], "remove": ["steam"]}
        self.cfg["declined"]["paru"] = ["fish"]
        self.cfg["declined"]["flatpak"] = ["com.spotify.Client"]
        r = S.resolve(self.repo, self.cfg)
        self.assertEqual(r["paru_install"], ["vulkan-radeon", "obs"])
        self.assertEqual(r["flatpak_install"], [])
        # declined is only "don't install"
        # local remove is a demotion (asdeps); repo remove stays a conflict swap
        self.assertEqual(r["paru_remove"], ["wine"])
        self.assertEqual(r["paru_demote"], ["steam"])
        self.assertNotIn("fish", r["paru_demote"])

    def test_features(self):
        self.assertEqual(S.features(self.repo, self.cfg), ["amd-gpu-tuning"])



    def test_write_plan_files_and_env(self):
        out = self.root / "plan"
        S.write_plan(self.repo, self.cfg, out)
        read = lambda n: (out / n).read_text().split()
        self.assertEqual(read("paru-install.list"), ["fish", "steam", "vulkan-radeon"])
        self.assertEqual(read("paru-remove.list"), ["wine"])
        self.assertEqual(read("flatpak-remove.list"), ["org.old.App"])
        self.assertEqual(read("projects.list"), ["git@x:dots.git", "git@x:app.git"])
        self.assertEqual((out / "project-builds.list").read_text(), "app\tmake install\n")
        self.assertEqual(read("stow.list"), ["alacritty", "fish"])
        self.assertEqual(read("systemd-enable.list"), ["cups", "bluetooth", "ollama"])
        self.assertEqual(read("systemd-user.list"), ["mpd"])
        self.assertEqual(read("npm-install.list"), ["@x/dsh"])
        self.assertEqual(read("uv-install.list"), ["graphifyy"])
        self.assertEqual((out / "ufw-allow.list").read_text(),
                         "2234/tcp\nfrom 192.168.1.0/24 to any port 22\n")
        self.assertEqual(read("paru-demote.list"), [])
        env = subprocess.run(["bash", "-c", f'source "{out}/env"; echo "$SYSUP_PROFILE|$SYSUP_DOTSET|$SYSUP_DOTSET_DIR|$SYSUP_FEATURES"'],
                             capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(env, f"desktop|mine|{self.dots}/dotsets/mine|amd-gpu-tuning")

    def test_write_plan_selections(self):
        out = self.root / "plan"
        S.write_plan(self.repo, self.cfg, out, stow_selected=["fish"], repos_selected=[])
        self.assertEqual((out / "stow.list").read_text().split(), ["fish"])
        self.assertEqual((out / "projects.list").read_text().split(), [])
        self.assertEqual((out / "project-builds.list").read_text(), "")

    def test_write_plan_dotset_none(self):
        self.cfg["dotset"] = "none"
        out = self.root / "plan"
        S.write_plan(self.repo, self.cfg, out)
        self.assertEqual((out / "stow.list").read_text(), "")
        env = subprocess.run(["bash", "-c", f'source "{out}/env"; echo "[$SYSUP_DOTSET_DIR]"'],
                             capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(env, "[]")




class PlanCommandTests(Tmp):
    def run_plan(self, host, cfg_text=None):
        if cfg_text is not None:
            self.cfg_path.parent.mkdir(exist_ok=True)
            self.cfg_path.write_text(cfg_text)
        env = {**os.environ, "SYSUP_CONFIG": str(self.cfg_path), "SYSUP_DOTS": str(self.dots),
               "HOSTNAME": host, }
        out = self.root / "plan"
        r = subprocess.run([sys.executable, "-B", str(HELPER), "plan", str(out)],
                           env=env, capture_output=True, text=True)
        return r, out

    def profile_of(self, out):
        return subprocess.run(["bash", "-c", f'source "{out}/env"; echo "$SYSUP_PROFILE $SYSUP_DOTSET"'],
                              capture_output=True, text=True).stdout.strip()

    def test_hostname_match_without_config(self):
        r, out = self.run_plan("my-surface-pro")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.profile_of(out), "surface mine")

    def test_config_wins_over_hostname(self):
        r, out = self.run_plan("my-surface-pro", 'profile = "desktop"\ndotset = "none"\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.profile_of(out), "desktop none")

    def test_invalid_config_falls_back_to_hostname(self):
        r, out = self.run_plan("desktop", 'profile = "deleted"\ndotset = "mine"\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.profile_of(out), "desktop mine")

    def test_broken_config_fails_clearly(self):
        r, _ = self.run_plan("desktop", 'profile = [\n')
        self.assertEqual(r.returncode, 2)
        self.assertIn("fix or delete", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_unknown_host_without_config_fails_clearly(self):
        r, out = self.run_plan("friends-laptop")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no profile for host 'friends-laptop'", r.stderr)
        self.assertIn("sysup --profile", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


HAS_TEXTUAL = importlib.util.find_spec("textual") is not None


class LastCheckTests(Tmp):
    def test_summary_from_last_check_file(self):
        f = self.root / "last-check.tsv"
        self.assertEqual(S.last_check(f), "")
        f.write_text("pacman-db\tok\n@warnings\t0\n")
        self.assertIn("check today: ok", S.last_check(f))
        f.write_text("pacman-db\tfail\nfirmware\tok\n@warnings\t2\n")
        self.assertIn("1 failed (pacman-db)", S.last_check(f))
        f.write_text("x\tok\n@warnings\t2\n")
        self.assertIn("2 warnings", S.last_check(f, now=f.stat().st_mtime + 3 * 86400))
        self.assertIn("3d ago", S.last_check(f, now=f.stat().st_mtime + 3 * 86400))


    def test_add_to_list_keeps_comments_and_shapes(self):
        f = self.root / "x.toml"
        f.write_text('# top\n[paru]\ninstall = [\n    "a",  # why a\n    # group\n]\nremove = ["r"]\n'
                     '[flatpak]\ninstall = ["f"]\n[npm]\nx = 1\n')
        for sec in ("paru", "flatpak", "npm", "uv"):
            S.add_to_list(f, sec, "new")
        text = f.read_text()
        self.assertIn("# why a", text)
        self.assertIn("# group", text)
        d = __import__("tomllib").loads(text)
        self.assertEqual(d["paru"], {"install": ["a", "new"], "remove": ["r"]})
        self.assertEqual(d["flatpak"]["install"], ["new", "f"])
        self.assertEqual(d["npm"], {"install": ["new"], "x": 1})
        self.assertEqual(d["uv"]["install"], ["new"])

    def test_add_to_list_refuses_to_write_broken_toml(self):
        f = self.root / "x.toml"
        f.write_text('[paru]\ninstall = [\n    "a",\n')  # unterminated
        with self.assertRaises(S.ConfigError):
            S.add_to_list(f, "paru", "new")
        self.assertEqual(f.read_text(), '[paru]\ninstall = [\n    "a",\n')




class UnusedTests(unittest.TestCase):
    def test_report_unlisted_idle_and_tracking_gate(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "paru-install.list").write_text("steam\ngimp\n")
            db = t / "wellbeing"
            db.mkdir()
            # BoltDB stores records as plain JSON between binary pages.
            (db / "db").write_bytes(b"\x00\x01" + b'{"date":"2026-01-01","active":5,"apps":{"Steam":60}}'
                                    + b"\xff" + b'{"date":"2026-03-01","active":5,"apps":{"steam":60}}')
            (t / "appusage.json").write_text('{"appUsageRanking":{"org.gimp.GIMP":{"lastUsed":1000}}}')
            seen = S.last_seen(t)
            installed = {"steam": {"steam"}, "gimp": {"org.gimp.gimp", "gimp"},
                         "stray": {"stray"}, "vim": set()}
            now = time.mktime(time.strptime("2026-03-10", "%Y-%m-%d"))
            (t / "ignore.list").write_text("base\n")
            (t / "paru-demote.list").write_text("old\n")
            explicit = {"steam", "gimp", "stray", "vim", "base", "old", "com.x.Y"}
            lines = S.report(t, 30, now, installed, seen, explicit)
            self.assertEqual(lines[0], "3 installed but in no package list: "
                                       "com.x.Y stray vim")
            self.assertIn("gimp (1970-01-01)", lines[1])
            self.assertIn("stray (never)", lines[1])
            self.assertNotIn("steam", lines[1])
            self.assertNotIn("vim", lines[1])  # terminal app: not trackable
            # Tracking younger than the window → no idle verdicts yet.
            lines = S.report(t, 100, now, installed, seen, explicit)
            self.assertTrue(lines[1].startswith("Unused-app check starts 2026-04-11"))

    def test_desktop_keys(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t, "com.spotify.Client.desktop")
            f.write_text("[Desktop Entry]\nExec=/usr/bin/flatpak run x\nStartupWMClass=spotify\n")
            self.assertEqual(S.desktop_keys(f), {"com.spotify.client", "client", "spotify"})
            f.write_text("[Desktop Entry]\nTerminal=true\n")
            self.assertEqual(S.desktop_keys(f), set())
            f.write_text("[Desktop Entry]\nNoDisplay=true\n")
            self.assertIsNone(S.desktop_keys(f))



class CommandTests(Tmp):
    def local(self):
        return tomllib.loads(self.cfg_path.read_text())

    def test_add_targets(self):
        for where, src in (("local", "paru"), ("remove", "paru"), ("ignore", "flatpak")):
            r = self.cli("add", where, src, "x")
            self.assertEqual(r.returncode, 0, r.stderr)
        d = self.local()
        self.assertEqual(d["paru"]["add"], ["x"])
        self.assertEqual(d["paru"]["remove"], ["x"])
        self.assertEqual(d["ignored"]["flatpak"], ["x"])

    def test_add_shared_and_profile_edit_repo_files(self):
        self.assertEqual(self.cli("add", "shared", "paru", "newpkg").returncode, 0)
        self.assertIn("newpkg", tomllib.loads((self.dots / "packages.toml").read_text())["paru"]["install"])
        self.assertEqual(self.cli("add", "profile", "flatpak", "com.x.Y", "surface").returncode, 0)
        self.assertEqual(tomllib.loads((self.dots / "profiles/surface.toml").read_text())["flatpak"]["install"],
                         ["com.x.Y"])

    def test_add_errors_write_nothing(self):
        r = self.cli("add", "profile", "paru", "x", "")
        self.assertEqual(r.returncode, 2)
        self.assertIn("sysup --profile", r.stderr)
        self.assertEqual(self.cli("add", "remove", "flatpak", "com.x.Y").returncode, 2)
        self.assertFalse(self.cfg_path.exists())

    def test_choose_validates_and_saves(self):
        r = self.cli("choose", "bogus")
        self.assertEqual(r.returncode, 2)
        self.assertIn("desktop, surface", r.stderr)
        r = self.cli("choose", "surface")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.local()["profile"], self.local()["dotset"]), ("surface", "mine"))
        self.assertEqual(self.cli("choose", "surface", "nope").returncode, 2)

    def test_once_done_skip_and_status(self):
        self.cli("choose", "desktop")
        self.assertEqual(self.cli("once-done", "services", "stow-symlinks").returncode, 0)
        self.assertEqual(self.cli("once-skip", "fish").returncode, 0)
        self.assertEqual(self.cli("once-skip", "stow-symlinks").returncode, 2)
        once = self.local()["once"]
        self.assertEqual(once, {"services": datetime.date.today(), "fish": "skip"})
        out = self.cli("status").stdout
        self.assertIn(f"services", out)
        self.assertIn(f"done {datetime.date.today()}", out)
        self.assertIn("skipped", out)
        self.assertNotIn("surface-secureboot", out)  # needs linux-surface feature

    def test_menu_rows_carry_label_state_and_hide_gated(self):
        self.cli("choose", "desktop")
        self.cli("once-done", "services")
        r = self.cli("menu", "sources", "services", "fish", "surface-secureboot")
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = [line.split("\t") for line in r.stdout.splitlines()]
        self.assertEqual([row[0] for row in rows], ["sources", "services", "fish"])  # gated one hidden
        self.assertTrue(all(len(row) == 5 for row in rows))
        self.assertEqual(rows[0][1:4], ["routine", "Refresh package sources", ""])  # repeatable: no state
        self.assertEqual(rows[1][3], f"done {datetime.date.today()}")
        self.assertEqual(rows[2][3], "never run")
        r = self.cli("menu", "sources", "nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("nope", r.stderr)

    def test_every_menu_order_id_has_a_menu_entry(self):
        script = (ROOT / "scripts/.local/bin/sysup").read_text()
        ids = next(l for l in script.splitlines() if l.startswith("MENU_ORDER=("))[12:-1].split()
        self.assertEqual(sorted(ids), sorted(S.ACTIONS))
        self.assertTrue(set(S.ONCE) <= set(ids))

    def test_migrates_old_config_once(self):
        xdg = self.root / "xdg"
        (xdg / "vjupdate").mkdir(parents=True)
        (xdg / "vjupdate/config.toml").write_text(
            'profile = "surface"\ndotset = "mine"\n[last]\nmaint = ["audit"]\ndotfiles = ["fish"]\n')
        r = self.cli("plan", str(self.root / "plan"), cfg=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("moved", r.stderr)
        new = tomllib.loads((xdg / "sysup/config.toml").read_text())
        self.assertEqual(new["profile"], "surface")
        self.assertEqual(new["select"], {"dotfiles": ["fish"]})
        self.assertNotIn("last", new)
        self.assertFalse((xdg / "vjupdate/config.toml").exists())
        self.assertEqual((self.root / "plan/stow.list").read_text(), "fish\n")

    def test_migration_never_overwrites_new_config(self):
        xdg = self.root / "xdg"
        for d, prof in (("vjupdate", "surface"), ("sysup", "desktop")):
            (xdg / d).mkdir(parents=True)
            (xdg / d / "config.toml").write_text(f'profile = "{prof}"\ndotset = "mine"\n')
        self.cli("plan", str(self.root / "plan"), cfg=False)
        self.assertIn("desktop", (xdg / "sysup/config.toml").read_text())
        self.assertTrue((xdg / "vjupdate/config.toml").exists())


if __name__ == '__main__':
    unittest.main()
