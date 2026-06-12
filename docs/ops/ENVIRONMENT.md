# Environment and Runtime Notes

Date created: 2026-06-12  
Source: Environment guidance moved out of the pre-Goal-0 `CLAUDE.md`.

## Repo and Branch Model

- Repository: `AdamsOdoo/Adams`.
- Review/merge branch: `review/full-audit`.
- Sessions develop on the harness/designated working branch.
- Never push directly to `review/full-audit`.
- Ahmed merges into `review/full-audit` via PR at approved checkpoints.

## Odoo.sh SSH / Relay Limitation

Odoo.sh runtime access is **not possible from session containers**. The previous project notes state that Claude Code cloud environments sit behind an HTTP/HTTPS-only egress proxy, so raw TCP/SSH on port 22 is unsupported under every network policy including “Full”. This was documented as confirmed against code.claude.com docs and empirically on 2026-06-11: port 22 timed out to all hosts, while port 443 to the same hosts connected.

Do not re-test SSH as an environment fix. Odoo.sh checks go through Ahmed as the relay/touchpoint.

Runtime strategy documented before Goal 0:

- **LOCAL:** an Odoo 19 Community runtime in the session container is used for iteration, audit verification against core source, and fail-before/pass-after evidence. The documented local stack was PostgreSQL 16, Python 3.11, and `odoo/odoo` branch 19.0 cloned over HTTPS. The connector dependencies were documented as Community modules: `product`, `sale_management`, `stock`, `contacts`, `mail`, and `account`.
- **ODOO.SH:** every Phase 2 fix stayed marked “pending Odoo.sh confirmation” in `FINALIZE.md` until tests also passed on the Odoo.sh build. Ahmed runs or relays those confirmation commands.
- Anything verifiable only against Enterprise code is flagged “unverified — needs build check”.

## Local Odoo Runtime Recipe

The pre-Goal-0 notes said local setup was “re-VERIFIED 2026-06-11 from scratch; baselines reproduced exactly.” This file preserves that historical claim from the old documentation; Goal 0 did not re-run or re-verify the runtime recipe.

Containers are ephemeral: the Odoo checkout, pip dependencies, PostgreSQL role, and all DB profiles are lost between sessions and must be rebuilt at session start.

Documented recipe:

- Odoo core: `/home/user/odoo` (`odoo/odoo` branch 19.0, shallow clone; 2026-06-11 tip `b4c7247f`, documented as suite-equivalent to the 2026-06-10 baseline commit `07a333c8`).
- PostgreSQL 16 local cluster: `pg_ctlcluster 16 main start`.
- DB superuser `root`: `su - postgres -c "createuser -s root && createdb root"`.

Do not create executable environment scripts in Goal 0.

## Python / pip Dependency Quirks

The old notes documented these Python 3.11 dependency quirks vs upstream requirements:

- Use `psycopg2-binary` instead of `psycopg2`.
- Use unpinned `rjsmin` and `vobject` because pinned versions fail to build.
- Use `docopt-ng` plus `num2words --no-deps`.
- Keep system `cryptography 41.0.7` with `urllib3==2.0.7` and `pyopenssl==24.1.0`.
- Add `beautifulsoup4`.
- Add `cffi`; without it, `odoo-bin` dies at startup with `ModuleNotFoundError` for `_cffi_backend` via OpenSSL import.
- Exclude `python-ldap` and `ofxparse`; old notes state build headers were unavailable and those packages were unused by the connector dependency set.

## PostgreSQL Notes

- PostgreSQL 16 local cluster was the documented local DB service.
- Create the `root` DB superuser and matching `root` database with:

```bash
su - postgres -c "createuser -s root && createdb root"
```

## One-DB-at-a-Time Rule

Run test DBs one at a time. The old notes state that `--test-tags` starts an HTTP server even with `--no-http`, causing port collisions, and that two parallel suite runs can OOM-kill PostgreSQL.

## Exact Test Command as Documented

Transcribed exactly from the old `CLAUDE.md`:

```bash
python3 /home/user/odoo/odoo-bin -d <db> --addons-path=/home/user/odoo/addons,/home/user/Adams/addons -u shopify_connector_pro,shopify_simulator,shopify_connector_pro_dashboard --test-tags /shopify_connector_pro,/shopify_simulator,/shopify_connector_pro_dashboard --stop-after-init --no-http --log-level=info
```

## DB Profiles

The old docs said DB profiles are rebuilt every session.

### `adams_test_fresh`

Fresh install, no chart of accounts. It exposes env sensitivity: 4 tests error because `account.tax` lacks `tax_group_id` (`AUDIT.md` ENV-1). Baseline documented on 2026-06-10: 0 failed, 4 errors of 532.

### `adams_strict1`

Install the 3 modules. The old notes warn that `l10n_generic_coa` is **not** a module in Odoo 19; the loader ignores it as an invalid module name, and the chart comes from the next step.

Apply the chart via Odoo shell:

```python
env['account.chart.template'].try_loading('generic_coa', env.company)
env.cr.commit()
```

Then run tests via `-u`, exercising the upgraded/existing-data path rather than only fresh install.

Baselines documented:

- 2026-06-10: 0 failed, 0 errors of 532.
- 2026-06-11 after rebuild: 0 failed, 0 errors of 552.

### `adams_strict_vat`

Clone `adams_strict1`:

```bash
createdb -T adams_strict1 adams_strict_vat
```

Then use Odoo shell to set:

- `env.company.account_price_include = 'tax_included'` (old notes cite `odoo/addons/account/models/company.py:282`).
- EUR activated.
- `base.group_multi_currency` implied for internal users.
- Explicit EUR exchange rate: `res.currency.rate`, 1 USD = 0.92 EUR.
- `env.cr.commit()`.

The old notes state this profile holds tax-included and multi-currency conditions simultaneously for the AUD-019/020/001 compound-bug surface.

Baselines documented:

- 2026-06-10: 1 failed, 0 errors of 532; caught AUD-001.
- 2026-06-11 after rebuild: 2 failed, 0 errors of 552; the known AUD-001 pair, both clear at 3e.

## Strict Profile Notes

The old docs said the strict DB definition was derived rather than recorded elsewhere. For each financial bug in legacy notes, determine the DB condition that surfaced it, such as localization/chart of accounts, multi-currency, rounding settings, constraints, and existing-data vs fresh-install behavior.

Documented reproduced strict conditions:

- Chart presence.
- Upgraded/existing-data path.
- VAT-inclusive plus multi-currency.

Known-relevant facts from Ahmed preserved from old notes:

- A UoM rounding fix in a sibling project was silently ignored on existing databases and needed a `post_init_hook`; always test upgraded/existing-data DBs, not only fresh installs.
- Include a VAT-inclusive-pricing localization among the profiles.
- Conditions that cannot be replicated on Community are flagged for the Odoo.sh confirmation pass.
