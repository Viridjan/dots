"""Tests for the vj Python package (config, resolution, plan, UI). No system changes."""
import datetime
import os
import subprocess
import sys
import tempfile
import unittest
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
        '[flatpak]\ninstall = ["com.spotify.Client"]\n')
    (d / "profiles/desktop.toml").write_text(
        'description = "Tower"\nhostname = "desktop"\ndotset = "mine"\nfeatures = ["amd-gpu-tuning"]\n'
        '[paru]\ninstall = ["vulkan-radeon", "fish"]\n')
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
        # local remove is a removal; declined is only "don't install"
        self.assertEqual(r["paru_remove"], ["wine", "steam"])
        self.assertNotIn("fish", r["paru_remove"])

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


if __name__ == "__main__":
    unittest.main()
