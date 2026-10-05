# Harness upgrade to 1.3.3

Installed from [MostafaEssamm12/Odoo at f6af65e](https://github.com/MostafaEssamm12/Odoo/tree/f6af65e1d2e9207528cf9ecd9c8d1fc15bf3aa1c) on 2026-10-05 using its `harness/install.py`, without `--force`. The [upstream port notes](https://github.com/MostafaEssamm12/Odoo/blob/f6af65e1d2e9207528cf9ecd9c8d1fc15bf3aa1c/harness/PORT-1.3.3.md) describe the shared payload.

The runtime, guard, skills, reviewer, scout and scoped rules are exact upstream payload copies. The installer generates the managed instruction block, hooks, permissions and lock. Adams keeps its project settings: production `main`, staging `staging` and `test`, Odoo commit `8d05257d83f9128953f580a066db67c48fcdb96f`, addon path `addons`, and English/Arabic. The active dashboard handoff is retained, with only its harness version and revision refreshed. The public-repository evidence policy and historical external adapter remain intact.

Validation: installer `--check` passed; reinstall was idempotent; upstream regression suite ran 120 tests, with 108 passing and 12 tests skipped (11 real-Odoo integration cases and one upgrade regression requiring the historical 1.1.0 checkout). The installed payload, hashes, hooks and settings were checked, together with the existing adapter tests. This is a harness port, not a new verification of Adams' business modules or a live Odoo.sh test. Review was a self-review.

The existing metadata workflow now also checks installed file hashes, instruction-block integrity, hooks and Claude/Codex skill parity on harness changes. It needs no access to the private upstream repository and does not run Odoo.

For the next update, use a clean current checkout of `MostafaEssamm12/Odoo` and run:

```bash
python3 /path/to/Odoo/harness/install.py /path/to/Adams --dry-run
python3 /path/to/Odoo/harness/install.py /path/to/Adams
python3 /path/to/Odoo/harness/install.py /path/to/Adams --check
```

Review conflicts rather than forcing replacement. Refresh the project-owned version references in `AGENTS.md` and `.odoo-harness/HANDOFF.md`, and publish on a feature branch. `.odoo-harness/lock.json` records the source repository, branch, exact revision and payload hashes. Updates are explicit installer runs; there is no background cross-repository overwrite. Only the owner deploys to production or staging.
