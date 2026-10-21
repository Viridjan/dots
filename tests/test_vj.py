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

from vj import config  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
