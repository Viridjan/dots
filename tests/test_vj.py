"""Tests for the vj Python package (config, resolution, plan, UI). No system changes."""
import asyncio
import datetime
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vj import config, resolve  # noqa: E402


def fixture_repo(root: Path) -> Path:
    """Minimal repo: two profiles, one dotset with two stow packages + profile dirs."""
    d = root / "dots"
    (d / "profiles").mkdir(parents=True)
    (d / "packages.toml").write_text(
        '[paru]\ninstall = ["fish", "git", "steam"]\nremove = ["wine"]\nhold = ["vectorcraft"]\nskip = ["git"]\n'
        '[flatpak]\ninstall = ["com.spotify.Client"]\n'
        '[systemd]\nenable = ["cups", "bluetooth"]\nuser = ["mpd"]\n[npm]\ninstall = ["@x/dsh"]\n[uv]\ninstall = ["graphifyy"]\n')
    (d / "profiles/desktop.toml").write_text(
        'description = "Tower"\nhostname = "desktop"\ndotset = "mine"\nfeatures = ["amd-gpu-tuning"]\n'
        '[paru]\ninstall = ["vulkan-radeon", "fish"]\n[systemd]\nenable = ["ollama", "cups"]\n')
    (d / "profiles/surface.toml").write_text(
        'description = "Tablet"\nhostname = "surface"\ndotset = "mine"\nfeatures = ["linux-surface"]\n')
    (d / "projects.toml").write_text('[[repo]]\nname = "dots"\nurl = "git@x:dots.git"\n')
    for p in ("alacritty", "fish", "desktop", "surface"):
        (d / "dotsets/mine" / p).mkdir(parents=True)
    return d


class Tmp(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="vj-test-")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.dots = fixture_repo(self.root)
        self.cfg_path = self.root / "cfg/config.toml"
        # recap() reads last-check.tsv from the state dir; keep the real one out.
        self.enterContext(patch.dict(os.environ, {"XDG_STATE_HOME": str(self.root / "state")}))


class ConfigTests(Tmp):
    def test_missing_file_gives_full_defaults(self):
        cfg = config.load_local(self.cfg_path)
        self.assertIsNone(cfg["profile"])
        self.assertEqual(cfg["paru"], {"add": [], "remove": []})
        self.assertEqual(cfg["declined"], {"paru": [], "flatpak": []})
        self.assertEqual(cfg["once"], {})
        self.assertEqual(cfg["last"], {})

    def test_partial_file_keeps_defaults_for_missing_keys(self):
        self.cfg_path.parent.mkdir()
        self.cfg_path.write_text('profile = "desktop"\n[paru]\nadd = ["obs"]\n')
        cfg = config.load_local(self.cfg_path)
        self.assertEqual(cfg["profile"], "desktop")
        self.assertEqual(cfg["paru"], {"add": ["obs"], "remove": []})
        self.assertEqual(cfg["flatpak"], {"add": [], "remove": []})

    def test_round_trip(self):
        cfg = config.load_local(self.cfg_path)
        cfg.update(profile="desktop", dotset="none")
        cfg["paru"]["add"] = ["obs-studio", 'we"ird']
        cfg["declined"]["flatpak"] = ["com.x.Y"]
        cfg["once"] = {"fish": datetime.date(2026, 10, 21), "keyring-pam": "skip"}
        cfg["last"] = {"repos": ["dots"], "maint": []}
        config.save_local(cfg, self.cfg_path)
        self.assertEqual(config.load_local(self.cfg_path), cfg)

    def test_broken_toml_gives_clear_error_not_traceback(self):
        self.cfg_path.parent.mkdir()
        self.cfg_path.write_text('profile = "desktop\n')  # unterminated string
        with self.assertRaises(config.ConfigError) as ctx:
            config.load_local(self.cfg_path)
        self.assertIn(str(self.cfg_path), str(ctx.exception))
        self.assertIn("fix or delete", str(ctx.exception))

    def test_save_is_atomic_no_leftovers(self):
        config.save_local(config.load_local(self.cfg_path), self.cfg_path)
        self.assertEqual([p.name for p in self.cfg_path.parent.iterdir()], ["config.toml"])

    def test_config_path_honours_env(self):
        old = os.environ.get("VJ_CONFIG")
        os.environ["VJ_CONFIG"] = str(self.cfg_path)
        self.addCleanup(lambda: os.environ.pop("VJ_CONFIG") if old is None else os.environ.update(VJ_CONFIG=old))
        self.assertEqual(config.config_path(), self.cfg_path)

    def test_load_repo(self):
        repo = config.load_repo(self.dots)
        self.assertEqual(sorted(repo.profiles), ["desktop", "surface"])
        self.assertEqual(repo.dotsets, ["mine"])
        self.assertEqual(repo.stow_pkgs("mine"), ["alacritty", "fish"])
        self.assertEqual(repo.stow_pkgs("none"), [])
        self.assertEqual(repo.projects[0]["name"], "dots")
        self.assertEqual(repo.packages["paru"]["hold"], ["vectorcraft"])

    def test_valid_choice(self):
        repo = config.load_repo(self.dots)
        cfg = config.load_local(self.cfg_path)
        self.assertFalse(config.valid_choice(cfg, repo))
        cfg.update(profile="desktop", dotset="mine")
        self.assertTrue(config.valid_choice(cfg, repo))
        cfg["dotset"] = "none"
        self.assertTrue(config.valid_choice(cfg, repo))
        cfg["dotset"] = "deleted"
        self.assertFalse(config.valid_choice(cfg, repo))
        cfg.update(profile="gone", dotset="mine")
        self.assertFalse(config.valid_choice(cfg, repo))


class ResolveTests(Tmp):
    def setUp(self):
        super().setUp()
        self.repo = config.load_repo(self.dots)
        self.cfg = config.load_local(self.cfg_path)
        self.cfg.update(profile="desktop", dotset="mine")

    def test_repo_plus_profile_minus_skip_deduped(self):
        r = resolve.resolve(self.repo, self.cfg)
        self.assertEqual(r["paru_install"], ["fish", "steam", "vulkan-radeon"])
        self.assertEqual(r["paru_hold"], ["vectorcraft"])
        self.assertEqual(r["paru_skip"], ["git"])
        self.assertEqual(r["flatpak_install"], ["com.spotify.Client"])

    def test_local_add_remove_and_declined(self):
        self.cfg["paru"] = {"add": ["obs"], "remove": ["steam"]}
        self.cfg["declined"]["paru"] = ["fish"]
        self.cfg["declined"]["flatpak"] = ["com.spotify.Client"]
        r = resolve.resolve(self.repo, self.cfg)
        self.assertEqual(r["paru_install"], ["vulkan-radeon", "obs"])
        self.assertEqual(r["flatpak_install"], [])
        # declined is only "don't install"
        # local remove is a demotion (asdeps); repo remove stays a conflict swap
        self.assertEqual(r["paru_remove"], ["wine"])
        self.assertEqual(r["paru_demote"], ["steam"])
        self.assertNotIn("fish", r["paru_demote"])

    def test_features(self):
        self.assertEqual(resolve.features(self.repo, self.cfg), ["amd-gpu-tuning"])

    def test_fmt_boundaries(self):
        self.assertEqual([resolve.fmt(s) for s in (0, 9, 10, 59, 60, 400)],
                         ["< 10 s", "< 10 s", "< 1 min", "< 1 min", "~1 min", "~7 min"])

    def test_fmt_c_colours(self):
        self.assertIn("#5fd75f", resolve.fmt_c(9))
        self.assertIn("#ffd75f", resolve.fmt_c(10))
        self.assertIn("#ff8700", resolve.fmt_c(60))
        self.assertIn("?", resolve.fmt_c(3, guessed=True))

    def test_estimate_precedence(self):
        times = {"aur:godot": 400, "@pacman-per-pkg": 5}
        self.assertEqual(resolve.estimate("paru", "godot", times), (400, False))
        self.assertEqual(resolve.estimate("paru", "fish", times), (5, False))
        self.assertEqual(resolve.estimate("flatpak", "x", times), (10, True))
        self.assertEqual(resolve.estimate("paru", "fish", {}), (3, True))

    def test_load_times(self):
        (self.dots / "build-times.tsv").write_text("aur:godot\t400\n@pacman-per-pkg\t5\nbad line\n")
        self.assertEqual(resolve.load_times(self.dots), {"aur:godot": 400, "@pacman-per-pkg": 5})

    def test_write_plan_files_and_env(self):
        out = self.root / "plan"
        resolve.write_plan(self.repo, self.cfg, out)
        read = lambda n: (out / n).read_text().split()
        self.assertEqual(read("paru-install.list"), ["fish", "steam", "vulkan-radeon"])
        self.assertEqual(read("paru-remove.list"), ["wine"])
        self.assertEqual(read("projects.list"), ["git@x:dots.git"])
        self.assertEqual(read("stow.list"), ["alacritty", "fish"])
        self.assertEqual(read("systemd-enable.list"), ["cups", "bluetooth", "ollama"])
        self.assertEqual(read("systemd-user.list"), ["mpd"])
        self.assertEqual(read("npm-install.list"), ["@x/dsh"])
        self.assertEqual(read("uv-install.list"), ["graphifyy"])
        self.assertEqual(read("paru-demote.list"), [])
        env = subprocess.run(["bash", "-c", f'source "{out}/env"; echo "$VJ_PROFILE|$VJ_DOTSET|$VJ_DOTSET_DIR|$VJ_FEATURES"'],
                             capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(env, f"desktop|mine|{self.dots}/dotsets/mine|amd-gpu-tuning")

    def test_write_plan_selections(self):
        out = self.root / "plan"
        resolve.write_plan(self.repo, self.cfg, out, stow_selected=["fish"], repos_selected=[])
        self.assertEqual((out / "stow.list").read_text().split(), ["fish"])
        self.assertEqual((out / "projects.list").read_text().split(), [])

    def test_write_plan_dotset_none(self):
        self.cfg["dotset"] = "none"
        out = self.root / "plan"
        resolve.write_plan(self.repo, self.cfg, out)
        self.assertEqual((out / "stow.list").read_text(), "")
        env = subprocess.run(["bash", "-c", f'source "{out}/env"; echo "[$VJ_DOTSET_DIR]"'],
                             capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(env, "[]")


class PlanCommandTests(Tmp):
    def run_plan(self, host, cfg_text=None):
        if cfg_text is not None:
            self.cfg_path.parent.mkdir(exist_ok=True)
            self.cfg_path.write_text(cfg_text)
        env = {**os.environ, "VJ_CONFIG": str(self.cfg_path), "VJ_DOTS": str(self.dots),
               "HOSTNAME": host, "PYTHONPATH": str(ROOT)}
        out = self.root / "plan"
        r = subprocess.run([sys.executable, "-B", "-m", "vj", "plan", str(out)],
                           env=env, capture_output=True, text=True)
        return r, out

    def profile_of(self, out):
        return subprocess.run(["bash", "-c", f'source "{out}/env"; echo "$VJ_PROFILE $VJ_DOTSET"'],
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
        self.assertIn("run 'vj'", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


HAS_TEXTUAL = importlib.util.find_spec("textual") is not None


class StateTests(Tmp):
    """UI-independent state behind the TUI (needs no Textual)."""

    def state(self, installed=("fish",)):
        from vj import state
        return state.State(config.load_repo(self.dots), self.cfg_path, installed=set(installed))

    def ready(self, **kw):
        st = self.state(**kw)
        st.choose("desktop", "mine")
        return st

    def test_choose_saves_profile(self):
        st = self.ready()
        self.assertEqual(config.load_local(self.cfg_path)["profile"], "desktop")
        self.assertTrue(st.ready())

    def test_unticking_package_declines_and_reticking_restores(self):
        st = self.ready()
        st.set_package("paru:steam", False)
        self.assertEqual(config.load_local(self.cfg_path)["declined"]["paru"], ["steam"])
        self.assertNotIn("steam", st.to_install()["paru"])
        st.set_package("paru:steam", True)
        self.assertEqual(config.load_local(self.cfg_path)["declined"]["paru"], [])
        # declined packages stay visible so they can be re-ticked
        self.assertIn("paru:steam", [i for i, _, _ in st.package_items()])

    def test_to_install_skips_installed(self):
        st = self.ready(installed=("fish", "steam"))
        self.assertEqual(st.to_install(), {"paru": ["vulkan-radeon"], "flatpak": ["com.spotify.Client"]})

    def test_recap_rows_are_counts_without_names(self):
        st = self.ready()
        pk = st.recap("packages")
        self.assertIn("install 3 packages", pk)
        self.assertNotIn("steam", pk)
        self.assertIn("desktop · mine", st.recap("settings"))
        self.assertIn("14 never run", st.recap("once"))

    def test_feature_gated_once_task_shows_only_with_feature(self):
        st = self.ready()
        self.assertNotIn("nvidia-niri", [i for i, _, _ in st.items("once")])
        prof = self.dots / "profiles/desktop.toml"
        prof.write_text(prof.read_text().replace('["amd-gpu-tuning"]', '["amd-gpu-tuning", "nvidia"]'))
        st = self.ready()
        self.assertIn("nvidia-niri", [i for i, _, _ in st.items("once")])
        self.assertFalse(dict((i, d) for i, _, d in st.items("once"))["nvidia-niri"])  # unticked by default
        self.assertIn("15 never run", st.recap("once"))

    def test_run_ids_follow_ticks_and_remember_last(self):
        st = self.ready()
        st.set_ticks("maint", ["sources", "install"])
        st.set_ticks("once", ["fish"])
        self.assertEqual(st.run_ids(), ["sources", "install", "fish"])
        self.assertEqual(config.load_local(self.cfg_path)["last"]["maint"], ["sources", "install"])
        # once ticks are per-run, not remembered
        self.assertNotIn("once", config.load_local(self.cfg_path)["last"])

    def test_results_stamp_once_tasks_only_on_ok(self):
        st = self.ready()
        res = self.root / "result.tsv"
        res.write_text("phase:configure\tok\naction:fish\tok\naction:vms\tfail\n")
        st.apply_results(res, today=datetime.date(2026, 10, 21))
        self.assertEqual(config.load_local(self.cfg_path)["once"], {"fish": datetime.date(2026, 10, 21)})

    def test_mark_once_skip_and_done(self):
        st = self.ready()
        st.mark_once("snapper", "skip")
        st.mark_once("fish", "done", today=datetime.date(2026, 1, 2))
        self.assertEqual(config.load_local(self.cfg_path)["once"],
                         {"snapper": "skip", "fish": datetime.date(2026, 1, 2)})
        self.assertIn("12 never run", st.recap("once"))

    def test_local_add_and_remove(self):
        st = self.ready()
        st.add_package("paru", "obs")
        st.toggle_remove("paru:steam")
        cfg = config.load_local(self.cfg_path)
        self.assertEqual(cfg["paru"], {"add": ["obs"], "remove": ["steam"]})
        self.assertIn("obs", st.to_install()["paru"])
        self.assertIn("remove 1", st.recap("packages"))

    def test_flatpak_remove_is_rejected_without_changing_selection(self):
        st = self.ready()
        self.assertFalse(st.toggle_remove("flatpak:com.spotify.Client"))
        self.assertEqual(st.cfg["flatpak"]["remove"], [])
        self.assertIn("com.spotify.Client", resolve.resolve(st.repo, st.cfg)["flatpak_install"])

    def test_legacy_flatpak_exclusion_is_not_reported_as_uninstall(self):
        st = self.ready()
        st.cfg["flatpak"]["remove"] = ["com.spotify.Client"]
        self.assertNotIn("remove", st.recap("packages"))

    def test_legacy_flatpak_exclusion_can_be_cleared(self):
        st = self.ready()
        st.cfg["flatpak"]["remove"] = ["com.spotify.Client"]
        self.assertTrue(st.toggle_remove("flatpak:com.spotify.Client"))
        self.assertEqual(st.cfg["flatpak"]["remove"], [])



class LastCheckTests(Tmp):
    def test_summary_from_last_check_file(self):
        from vj import state
        f = self.root / "last-check.tsv"
        self.assertEqual(state.last_check(f), "")
        f.write_text("pacman-db\tok\n@warnings\t0\n")
        self.assertIn("check today: ok", state.last_check(f))
        f.write_text("pacman-db\tfail\nfirmware\tok\n@warnings\t2\n")
        self.assertIn("1 failed (pacman-db)", state.last_check(f))
        f.write_text("x\tok\n@warnings\t2\n")
        self.assertIn("2 warnings", state.last_check(f, now=f.stat().st_mtime + 3 * 86400))
        self.assertIn("3d ago", state.last_check(f, now=f.stat().st_mtime + 3 * 86400))

class UnlistedTests(Tmp):
    """#4: explicitly installed packages in no list, sorted from vj."""

    def state(self):
        from vj import state
        st = state.State(config.load_repo(self.dots), self.cfg_path, installed={"fish"},
                         explicit={"fish": "paru", "wine": "paru", "git": "paru", "base": "paru", "obs": "paru",
                                   "kicad": "paru", "zed": "paru", "old": "paru", "com.x.Y": "flatpak"})
        st.choose("desktop", "mine")
        return st

    def test_unlisted_excludes_lists_skip_and_repo_removes(self):
        self.assertEqual(self.state().unlisted(), [("flatpak", "com.x.Y"), ("paru", "base"), ("paru", "kicad"),
                                                   ("paru", "obs"), ("paru", "old"), ("paru", "zed")])

    def test_audit_keeps_declined_packages_known_without_installing_them(self):
        from vj import unused
        st = self.state()
        st.set_package('paru:steam', False)
        st.set_package('flatpak:com.spotify.Client', False)
        plan = self.root / 'plan'
        st.write_plan(plan)
        self.assertNotIn('steam', (plan / 'paru-install.list').read_text().split())
        self.assertNotIn('com.spotify.Client', (plan / 'flatpak-install.list').read_text().split())
        lines = unused.report(plan, 60, installed={}, seen=({}, None),
                              explicit={'steam', 'com.spotify.Client', 'stray'})
        self.assertEqual(lines[0], '1 installed but in no package list (sort them in vj → Unlisted packages): stray')

    def test_each_choice_moves_it_out_and_persists(self):
        st = self.state()
        st.sort_unlisted(["paru:base", "flatpak:com.x.Y"], "ignore")
        st.sort_unlisted(["paru:obs"], "machine")
        st.sort_unlisted(["paru:old", "flatpak:com.x.Y"], "demote")  # flatpak: never uninstalled
        self.assertIn("1 package", st.sort_unlisted(["paru:kicad"], "repo"))
        st.sort_unlisted(["paru:zed"], "profile")
        self.assertEqual(st.unlisted(), [])
        cfg = config.load_local(self.cfg_path)
        self.assertEqual(cfg["ignored"], {"paru": ["base"], "flatpak": ["com.x.Y"]})
        self.assertEqual(cfg["paru"], {"add": ["obs"], "remove": ["old"]})
        self.assertEqual(cfg["flatpak"]["remove"], [])
        repo = config.load_repo(self.dots)
        self.assertIn("kicad", repo.packages["paru"]["install"])
        self.assertIn("zed", repo.profiles["desktop"]["paru"]["install"])
        resolve.write_plan(repo, cfg, self.root / "plan")
        self.assertEqual((self.root / "plan/ignore.list").read_text(), "base\ncom.x.Y\n")

    def test_recap(self):
        st = self.state()
        self.assertIn("6 packages to sort", st.recap("unlisted"))
        st.sort_unlisted([f"{s}:{n}" for s, n in st.unlisted()], "ignore")
        self.assertIn("none", st.recap("unlisted"))

    def test_add_to_list_keeps_comments_and_shapes(self):
        f = self.root / "x.toml"
        f.write_text('# top\n[paru]\ninstall = [\n    "a",  # why a\n    # group\n]\nremove = ["r"]\n'
                     '[flatpak]\ninstall = ["f"]\n[npm]\nx = 1\n')
        for sec in ("paru", "flatpak", "npm", "uv"):
            config.add_to_list(f, sec, "new")
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
        with self.assertRaises(config.ConfigError):
            config.add_to_list(f, "paru", "new")
        self.assertEqual(f.read_text(), '[paru]\ninstall = [\n    "a",\n')


@unittest.skipUnless(HAS_TEXTUAL, "textual not installed")
class UiTests(Tmp):
    def setUp(self):
        super().setUp()
        runtime = self.root / "runtime"
        runtime.mkdir()
        self.enterContext(patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)}))

    def app(self, runner=None):
        from vj import ui
        return ui.VjApp(config.load_repo(self.dots), self.cfg_path, installed=set(), runner=runner, host="desktop")

    def drive(self, coro):
        return asyncio.run(asyncio.wait_for(coro, 30))

    def test_first_run_opens_setup_and_enter_saves(self):
        async def go():
            app = self.app()
            async with app.run_test() as pilot:
                await pilot.pause()
                self.assertTrue(app.screen.query("SetupPanel"))
                await pilot.press("enter")
                await pilot.pause()
                self.assertFalse(app.screen.query("SetupPanel"))
        self.drive(go())
        cfg = config.load_local(self.cfg_path)
        self.assertEqual((cfg["profile"], cfg["dotset"]), ("desktop", "mine"))

    def test_q_closes_panel_then_quits_from_menu(self):
        cfg = config.load_local(self.cfg_path)
        cfg.update(profile='desktop', dotset='mine')
        config.save_local(cfg, self.cfg_path)

        async def go():
            app = self.app()
            async with app.run_test() as pilot:
                await pilot.press('enter')
                await pilot.pause()
                self.assertTrue(app.screen.query('Checklist'))
                await pilot.press('q')
                await pilot.pause()
                self.assertFalse(app.screen.query('Checklist'))
                self.assertTrue(app.is_running)
                await pilot.press('q')
                await pilot.pause()
                self.assertFalse(app.is_running)
        self.drive(go())

    def test_q_quits_initial_setup_without_requiring_a_profile(self):
        async def go():
            app = self.app()
            async with app.run_test() as pilot:
                await pilot.press('q')
                await pilot.pause()
                self.assertFalse(app.is_running)
        self.drive(go())

    def test_default_run_opens_progress_and_cleans_plan_on_return(self):
        from vj.progress import RunScreen
        cfg = config.load_local(self.cfg_path)
        cfg.update(profile="desktop", dotset="mine")
        config.save_local(cfg, self.cfg_path)
        script = self.dots / 'scripts/.local/bin/vjupdate'
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text('#!/bin/sh\nprintf "phase:install\\tok\\n" >> "$VJ_RESULT_FILE"\necho finished\n')
        script.chmod(0o755)

        async def go():
            app = self.app()
            async with app.run_test() as pilot:
                await pilot.press('r')
                await pilot.pause()
                self.assertIsInstance(app.screen, RunScreen)
                screen = app.screen
                plan = screen.results.parent
                for _ in range(100):
                    await pilot.pause(0.02)
                    if screen.returncode is not None:
                        break
                self.assertEqual(screen.returncode, 0)
                self.assertTrue(plan.exists())
                await pilot.press('q')
                await pilot.pause()
                self.assertFalse(isinstance(app.screen, RunScreen))
                self.assertFalse(plan.exists())
        self.drive(go())

    def test_menu_rows_show_recap_and_run_calls_runner(self):
        calls = []

        def runner(ids, env):
            calls.append((ids, env, (Path(env["VJ_PLAN_DIR"]) / "paru-install.list").read_text().split()))
            Path(env["VJ_RESULT_FILE"]).write_text("action:fish\tok\n")
            return 0

        cfg = config.load_local(self.cfg_path)
        cfg.update(profile="desktop", dotset="mine")
        config.save_local(cfg, self.cfg_path)

        async def go():
            app = self.app(runner)
            async with app.run_test() as pilot:
                await pilot.pause()
                rows = [str(app.screen.menu_row(i)) for i in range(len(app.screen.MENU))]
                self.assertTrue(any("install 4 packages" in r for r in rows), rows)
                app.state.set_ticks("once", ["fish"])
                await pilot.press("r")
                await pilot.pause()
        self.drive(go())
        self.assertEqual(len(calls), 1)
        ids, env, planned = calls[0]
        self.assertIn("fish", ids)
        self.assertEqual(planned, ["fish", "steam", "vulkan-radeon"])
        self.assertFalse(Path(env["VJ_PLAN_DIR"]).exists())  # cleaned up after the run
        self.assertIn("fish", config.load_local(self.cfg_path)["once"])


if __name__ == "__main__":
    unittest.main()


class UnusedTests(unittest.TestCase):
    def test_report_unlisted_idle_and_tracking_gate(self):
        from vj import unused
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "paru-install.list").write_text("steam\ngimp\n")
            db = t / "wellbeing"
            db.mkdir()
            # BoltDB stores records as plain JSON between binary pages.
            (db / "db").write_bytes(b"\x00\x01" + b'{"date":"2026-01-01","active":5,"apps":{"Steam":60}}'
                                    + b"\xff" + b'{"date":"2026-03-01","active":5,"apps":{"steam":60}}')
            (t / "appusage.json").write_text('{"appUsageRanking":{"org.gimp.GIMP":{"lastUsed":1000}}}')
            seen = unused.last_seen(t)
            installed = {"steam": {"steam"}, "gimp": {"org.gimp.gimp", "gimp"},
                         "stray": {"stray"}, "vim": set()}
            now = time.mktime(time.strptime("2026-03-10", "%Y-%m-%d"))
            (t / "ignore.list").write_text("base\n")
            (t / "paru-demote.list").write_text("old\n")
            explicit = {"steam", "gimp", "stray", "vim", "base", "old", "com.x.Y"}
            lines = unused.report(t, 30, now, installed, seen, explicit)
            self.assertEqual(lines[0], "3 installed but in no package list (sort them in vj → Unlisted packages): "
                                       "com.x.Y stray vim")
            self.assertIn("gimp (1970-01-01)", lines[1])
            self.assertIn("stray (never)", lines[1])
            self.assertNotIn("steam", lines[1])
            self.assertNotIn("vim", lines[1])  # terminal app: not trackable
            # Tracking younger than the window → no idle verdicts yet.
            lines = unused.report(t, 100, now, installed, seen, explicit)
            self.assertTrue(lines[1].startswith("Unused-app check starts 2026-04-11"))

    def test_desktop_keys(self):
        from vj import unused
        with tempfile.TemporaryDirectory() as t:
            f = Path(t, "com.spotify.Client.desktop")
            f.write_text("[Desktop Entry]\nExec=/usr/bin/flatpak run x\nStartupWMClass=spotify\n")
            self.assertEqual(unused.desktop_keys(f), {"com.spotify.client", "client", "spotify"})
            f.write_text("[Desktop Entry]\nTerminal=true\n")
            self.assertEqual(unused.desktop_keys(f), set())
            f.write_text("[Desktop Entry]\nNoDisplay=true\n")
            self.assertIsNone(unused.desktop_keys(f))
