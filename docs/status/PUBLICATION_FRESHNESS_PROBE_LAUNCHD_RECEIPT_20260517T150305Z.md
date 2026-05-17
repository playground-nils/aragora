# Publication Freshness Probe LaunchAgent — Install Template Receipt

**Generated:** `2026-05-17T15:03:05Z`
**Author:** Factory Droid (`droid/phase4-freshness-launchagent-20260517`)
**Status:** template + installer, opt-in only

## Goal

PR #7261 publishes a recurring publication-freshness probe receipt
(`scripts/publish_publication_freshness_probe.py`) and a human-readable
status surface (`docs/status/PUBLICATION_FRESHNESS_PROBE_STATUS.md`).
To stay fresh, the probe needs to run on a schedule. Until now the only
way to refresh it was for an operator to run the command manually.

This receipt documents the macOS LaunchAgent template and the opt-in
installer that lets a workstation schedule the probe to run every
4 hours without touching any agent dispatch, admission policy, or other
automation.

## What this ships

### 1. `scripts/launch_agents/com.aragora.publication-freshness-probe.plist`

A path-agnostic LaunchAgent plist template with two placeholders:

- `__ARAGORA_REPO_ROOT__` — absolute path to the Aragora checkout
- `__ARAGORA_PYTHON__` — absolute path to a Python 3 interpreter

Defaults:

- `Label`: `com.aragora.publication-freshness-probe`
- `StartInterval`: `14400` seconds (4 hours)
- `RunAtLoad`: `true`
- Probe command: `<python> scripts/publish_publication_freshness_probe.py --render-markdown`
- Log paths: `<repo>/.worktrees/publication-freshness-probe.log`
  (matches the existing convention used by
  `scripts/install_worktree_maintainer_launchd.sh`).

Validated with `plutil -lint`. No `/Users/armand` or other workstation-
specific paths in the template — tests enforce that with
`test_template_uses_placeholders_only`.

### 2. `scripts/install_publication_freshness_probe_launchd.sh`

Opt-in installer that

1. reads the template,
2. substitutes the two placeholders + the optional `StartInterval`,
3. writes the rendered plist to
   `~/Library/LaunchAgents/com.aragora.publication-freshness-probe.plist`,
4. `launchctl unload`s any previous instance (best-effort) and
   `launchctl load`s the new instance.

Flags:

- `--interval-seconds <n>` — override `StartInterval` (default 14400)
- `--python <path>` — override Python interpreter (default `.venv/bin/python3`
  if present, else `python3` on `PATH`)
- `--uninstall` — `launchctl unload` + `rm` of the rendered plist
- `--dry-run` — render the plist to stdout without installing anything
- `--help` — print usage

Strictly opt-in: no other script in `scripts/` invokes this installer.
Tests enforce that with `test_installer_no_automation_invokes_it`.

### 3. `tests/scripts/test_install_publication_freshness_probe_launchd.py`

15-test suite covering:

- template exists, declares XML prolog, plist DOCTYPE, root element
- template uses placeholders only, no workstation paths
- label matches filename
- template runs the freshness probe with `--render-markdown`
- default interval is 4 hours (`14400`)
- installer `--help` exits 0
- installer rejects unknown flags with exit code 2
- installer rejects non-numeric `--interval-seconds` with exit code 2
- installer `--dry-run` substitutes `__ARAGORA_REPO_ROOT__` and
  `__ARAGORA_PYTHON__`
- installer `--dry-run` changes `StartInterval`
- installer `--dry-run` output parses as valid plist XML and contains
  the LaunchAgent label
- installer `--dry-run` writes nothing under `$HOME/Library/LaunchAgents`
- installer `--uninstall` is idempotent (does not fail when nothing is
  installed)
- no other `.sh` or `.py` under `scripts/` invokes the installer
- installer carries an executable shebang and `+x` bit

All 15 new tests + the 11 pre-existing freshness probe tests pass:

```
$ pytest tests/scripts/test_install_publication_freshness_probe_launchd.py \
         tests/scripts/test_publish_publication_freshness_probe.py -q
..........................                                              26 passed
```

## Why not auto-install

LaunchAgents persist across reboots and run under the logged-in user's
session. Installing one silently is high-trust. This is opt-in by design
so an operator decides

- which Python interpreter the probe uses,
- how often it runs,
- whether it gets installed at all on a given workstation.

The repo ships the *template* and the *installer*. Neither is invoked
automatically. Operators can dry-run the installer to inspect the
rendered plist before deciding.

## What is NOT in this PR

- No change to `scripts/publish_publication_freshness_probe.py` itself.
- No new flags, no behavior change in the probe.
- No protected file touched.
- No automation in `scripts/` calls the installer (asserted by a test).
- No automatic load of the plist; the rendered file is what `launchctl
  load` would consume.

## Reproduction

```
$ /bin/bash scripts/install_publication_freshness_probe_launchd.sh --help
$ /bin/bash scripts/install_publication_freshness_probe_launchd.sh \
    --dry-run \
    --python /usr/bin/python3 \
    --interval-seconds 7200
$ /bin/bash scripts/install_publication_freshness_probe_launchd.sh    # actually install
$ /bin/bash scripts/install_publication_freshness_probe_launchd.sh --uninstall
```

## Relationship to PR #7261

This branch is built on top of the PR #7261 branch
(`droid/phase4-publication-freshness-probe-20260516`). #7261 can land
first, or this PR can be reviewed in tandem. If reviewed standalone, the
diff is small: 4 new files.
