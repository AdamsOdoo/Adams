# Odoo Credential Storage Official Notes

> **Acceptance note (2026-07-06):** ChatGPT accepted this research as
> **sufficient evidence for the official Community/core Odoo 19 scope
> reviewed** (see [AR-022](../05-qa/architecture-review-log.md), Accepted
> 2026-07-06). This note records that acceptance only — the accepted
> **mechanism direction (Option B)** and MBQ-04's **Partially resolved**
> classification are recorded in
> [`../03-architecture/mbq-04-credential-persistence-decision-proposal.md`](../03-architecture/mbq-04-credential-persistence-decision-proposal.md)
> and in `../03-architecture/master-blueprint-open-questions.md` (MBQ-04),
> not in this research document, which is left otherwise unchanged.

## Scope

This document researches **MBQ-04 only** — the exact credential/secret/token
storage-at-rest mechanism a future Shopify Admin API credential could use in the
Odoo 19 ↔ Shopify Connector. **It does not authorize implementation.** It does
not create a credential model, a credential field, an API client, a setup
wizard, or a test-connection mechanism, and it does not itself change MBQ-04's
recorded status in `../03-architecture/master-blueprint-open-questions.md`
(that file is outside this session's allowed-files scope; any register update
is left to a future ChatGPT-reviewed acceptance patch, per this project's usual
proposal → review → acceptance-patch pattern). Every fact below is drawn from
an official Odoo 19.0 source and was independently, adversarially re-verified
against its cited URL before inclusion here (each claim was fetched a second
time by a separate reviewer instructed to try to refute or narrow it). **Access
date for every source below: 2026-07-05**, unless noted otherwise.

Per `CLAUDE.md` §8, every statement below is labelled **Fact** (official doc
prose), **Official source-code fact** (verified against Odoo's own `19.0`
source), **Inference** (our deduction from the facts), or **Open question**
(not settled by any source reviewed this session). No claim in this document
should be read as a Decision — decisions live only in `/docs/04-decisions`
after ChatGPT review.

## Sources searched

**Official Odoo 19.0 documentation** (`odoo.com/documentation/19.0/**`):

- `/developer/reference/backend/orm.html` — ORM API reference (`Field`/`Char`
  constructor parameters)
- `/developer/reference/user_interface/view_architectures.html` — View
  Architectures reference (the `password` view-arch attribute)
- `/developer/reference/backend/security.html` — access rights, record rules,
  field-level `groups`
- `/developer/reference/backend/data.html`
- `/developer/reference/external_api.html` — API key generation/management
  guidance
- `/applications/general/users/azure.html` — the only official admin-facing
  page found demonstrating a concrete `ir.config_parameter` System Parameter
- `/administration/odoo_sh.html` and its 9 subsections (Create a project,
  Branches, Builds, Settings, Online editor, Create a module, Advanced,
  Containers, Submodules, Frequent Technical Questions)
- `/administration/odoo_online.html`
- `/administration/on_premise/deploy.html` — master `admin_passwd`,
  `db_password`

**Official Odoo 19.0 source code** (`github.com/odoo/odoo`, branch `19.0`,
fetched as raw content via `raw.githubusercontent.com`):

- `odoo/orm/fields.py`, `odoo/orm/fields_textual.py` — `Field`/`Char`/`Text`/
  `Html` base classes
- `odoo/orm/models.py` — `BaseModel`, `sudo()`, `_has_field_access`, `read`,
  `fields_get`, `_read_format`
- `odoo/addons/base/models/ir_config_parameter.py`
- `odoo/addons/base/models/ir_model.py`, `odoo/addons/base/models/ir_rule.py`
- `odoo/addons/base/models/res_users.py` — login-password compute/inverse/hash
- `odoo/addons/base/models/ir_mail_server.py` — `smtp_pass`
- `odoo/addons/base/security/ir.model.access.csv`
- `addons/payment/models/payment_provider.py`, `addons/payment/const.py`
- `addons/payment_stripe/models/payment_provider.py`
- `addons/payment_adyen/models/payment_provider.py`
- `addons/payment_authorize/models/payment_provider.py`
- `addons/iap/models/iap_account.py`
- `addons/auth_oauth/models/auth_oauth.py`
- `addons/web/static/src/views/fields/password/password_field.js` (+ `.xml`),
  `addons/web/static/src/views/fields/char/char_field.js` (+ `.xml`),
  `addons/web/static/src/views/fields/formatters.js`

**Official first-party Odoo pages, not versioned developer docs** (distinguished
explicitly wherever cited below):

- `odoo.com/security` — corporate security page
- `odoo.com/gdpr` — corporate GDPR page

**Explicitly excluded as evidence**, per this task's hard rules: blogs, forums,
Stack Overflow, third-party tutorials, and OCA/community modules. None were
used as a fact source; where one was encountered while searching, it was
discarded.

## Confirmed facts

### `password` is a view/UI attribute, not an ORM field-storage mechanism

- **Fact —** The `password` attribute is documented in the official **View
  Architectures** reference (not the ORM API reference) as a `<field>` arch
  attribute: *"Whether the field stores a password and thus its data should not
  be displayed."* Type `bool`, default `False`, scope "Char fields."
  (https://www.odoo.com/documentation/19.0/developer/reference/user_interface/view_architectures.html)
- **Fact —** The official **ORM API reference** documents `odoo.fields.Char`'s
  constructor with exactly three parameters — `size`, `trim`, `translate` — no
  `password` parameter exists for `Char` or any other field class on that page.
  The literal word "password" appears on that page only twice, both in
  unrelated `AccessDenied`-exception prose ("Login/password error.", "...wrong
  password."), never as a field parameter.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)
- **Official source-code fact —** The word `password` does not appear anywhere
  in Odoo 19.0's `odoo/orm/fields.py` (base `Field` class) or
  `odoo/orm/fields_textual.py` (`BaseString`/`Char`/`Text`/`Html`). No
  `_description_password` method or `password` class attribute exists, so
  `fields_get()` — which builds its per-field metadata dict solely from methods
  named `_description_<attr>` — can never expose a `password` key for any
  field, regardless of any kwarg passed.
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/fields.py;
  https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/fields_textual.py)
- **Official source-code fact —** Odoo's base `Field.__init__` accepts
  arbitrary `**kwargs`; an unrecognized parameter name is only accepted if the
  model's `_valid_field_parameter(field, name)` allows it. The default
  `BaseModel._valid_field_parameter` implementation is `return name ==
  'related_sudo'` — i.e. **only `related_sudo` is accepted as an extra
  parameter by default; a bare `fields.Char(password=True)` on an ordinary
  model is not a recognized ORM parameter and only logs an "unknown parameter"
  warning** unless that specific model overrides the check.
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/models.py;
  https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/fields.py)
- **Official source-code fact —** The real masking mechanism lives entirely in
  the **web client** (JavaScript), driven by the view-arch `password` attribute
  read off the `<field>` XML node — not by any ORM-level field metadata. The
  `PasswordField` and `CharField` (with `isPassword`) widgets both mask only
  what is *rendered*, operating on `this.props.record.data[...]` — a value
  **already delivered to the browser** by a prior `read()`/`web_read` RPC call.
  `CharField`'s readonly rendering shows asterisks equal to the actual value's
  length via `formatChar()`; `PasswordField`'s readonly rendering shows a fixed
  16-character decoy (not length-revealing) and offers an eye-icon reveal
  toggle in both readonly and edit modes. Either way, **the true value is
  already resident client-side before any masking is applied — masking is a
  display transform, not an access or transport restriction.**
  (https://raw.githubusercontent.com/odoo/odoo/19.0/addons/web/static/src/views/fields/password/password_field.js
  and `.xml`; `addons/web/static/src/views/fields/char/char_field.js` and
  `.xml`; `addons/web/static/src/views/fields/formatters.js`)
- **Official source-code fact —** No password-specific branch exists in the
  core ORM read/write/`fields_get` pipeline: the literal word "password" occurs
  exactly once in the full `odoo/orm/models.py` (7,129 lines), in an unrelated
  code comment referencing a website password-reset test-tour name.
  `fields_get()`, `read()`, and `_read_format()` (all defined in this file)
  contain no password-specific logic.
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/models.py)

### Odoo's own login-password field does not rely on the `password` attribute — it uses compute-blanking plus one-way hashing

- **Official source-code fact —** `res.users.password` is declared as a
  **compute/inverse** `Char` field (no `password=True` kwarg, no `groups=`
  restriction on the field declaration itself). Its compute method
  unconditionally blanks the value on every read (`user.password = ''`), so an
  ORM `read()` never returns the stored value for this field. Its inverse
  computes a **one-way hash** via a passlib-style `CryptContext` and writes it
  with **raw SQL** (`UPDATE res_users SET password=%s`), bypassing the normal
  ORM write path, and explicitly asserts the value is not stored as plaintext
  (`assert self._crypt_context().identify(pw) != 'plaintext'`).
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/res_users.py)
- **Inference —** This is a distinct, purpose-built security mechanism for the
  login password specifically (compute-blank + one-way hash) — not a generic
  capability that `fields.Char(password=True)` grants to any field. Nothing in
  the reviewed source shows this hashing mechanism reused, exposed, or made
  available as a generic "make this field encrypted" ORM feature for arbitrary
  connector credentials.

### `ir.config_parameter` — plain key/value configuration storage, access-controlled but unencrypted

- **Official source-code fact —** The model's own docstrings describe it as
  generic configuration storage, not a secrets vault: module docstring "Store
  database-specific configuration parameters"; class docstring "Per-database
  storage of configuration key-value pairs."
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/ir_config_parameter.py)
- **Official source-code fact —** `key` is a plain required `Char`; `value` is
  a plain required `Text`. No import of any hashing/crypto library and no
  encryption/hashing/obfuscation call exists anywhere in the file (`get_param`,
  `_get_param`, `set_param`, `create`, `write`, `init`). `_get_param` even reads
  the value via **raw SQL** (`SELECT value FROM ir_config_parameter WHERE key =
  %s`). (same source)
- **Official source-code fact —** `get_param()` calls
  `self.browse().check_access('read')` before returning a value — ordinary ORM
  access-control enforcement, not encryption. (same source)
- **Official source-code fact —** The only access-rights row for this model in
  the base module's ACL file grants full CRUD (`1,1,1,1`) **exclusively to
  `group_system`**; no other group has any row for this model.
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/security/ir.model.access.csv)
- **Official source-code fact —** `_allow_sudo_commands = False` is set on the
  model, but no docstring/comment in this file, or anywhere else checked this
  session, explains its exact runtime semantics — logged as an open question,
  not interpreted as an encryption or confidentiality control.
- **Official source-code fact —** Odoo's own core code stores a generated
  secret-like value, `database.secret` (`str(uuid.uuid4())`), through this
  exact same plain-`Text`/`group_system`-only mechanism, alongside non-sensitive
  values like `web.base.url` — with **no additional protection** applied to
  `database.secret` versus any other parameter. Renaming or deleting any key
  listed in `_default_parameters` (including `database.secret`/`database.uuid`)
  is blocked with a `ValidationError` — an **integrity/referential-safety
  guard**, not a confidentiality control (the *value* can still be changed by
  anyone with write access). (same source)
- **Fact —** The only official 19.0 admin-facing documentation page found
  naming a concrete System Parameters usage example (`Settings ▸ Technical ▸
  System Parameters`, gated behind Developer Mode) shows a config **flag**
  (`auth_oauth.authorization_header = 1`) for Microsoft Azure OAuth login
  setup — not a secret value — and gives no guidance on data sensitivity or
  encryption. (https://www.odoo.com/documentation/19.0/applications/general/users/azure.html)
- **Open question —** No official 19.0 documentation page checked this session
  (`orm.html`, `data.html`, `security.html`, `on_premise/deploy.html`)
  characterizes `ir.config_parameter` as encrypted or as a secure secrets
  store; all four were searched and contain no such statement. Absence of
  documentation on these four pages is not proof no such statement exists on
  some other, unchecked official page.

### Access rights, record rules, and field-level `groups` are access control — not encryption

- **Fact —** A Field's `groups` attribute (comma-separated group external IDs)
  removes the field from requested views, removes it from `fields_get()`
  responses, and raises an access error on an explicit read/write attempt by a
  user outside those groups.
  (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html,
  "Field Access")
- **Official source-code fact —** The ORM source's own docstring for the
  `groups` field parameter states plainly: *"comma-separated list of group xml
  ids (string); this restricts the field access to the users of the given
  groups only"* — no mention of encryption anywhere in the file.
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/fields.py)
- **Fact —** `ir.model.access` grants whole-model CRUD via `res.groups`
  membership, additive across a user's groups ("Access rights are additive, a
  user's accesses are the union of the accesses they get through all their
  groups"); `perm_{read,write,create,unlink}` are "all unset by default."
  `ir.rule` applies a `domain_force` predicate record-by-record, is
  default-allow, and combines as **global rules intersect (AND)** / **group
  rules unify (OR)**, with the global and group rulesets themselves
  intersecting. (https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
  Neither mechanism is documented anywhere on this page as providing
  encryption.
- **Official source-code fact —** `sudo()` (superuser mode) "does not change
  the current user, and simply bypasses access rights checks," and its own
  docstring warns it "could cause data access to cross the boundaries of
  record rules."
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/models.py, `sudo()`)
- **Official source-code fact —** **`sudo()`/superuser mode explicitly bypasses
  field-level `groups` protection too**, not just model/record-level access:
  `_has_field_access`'s first check is `if not field.groups or self.env.su:
  return True` — superuser mode short-circuits to granted *before* even the
  field's own `NO_ACCESS` sentinel or the user's group membership is checked.
  Odoo even defines a maximally-restrictive sentinel value, `NO_ACCESS = '.'`,
  with its own source comment candidly describing it as *"a hacky-ish way to
  prevent access to a field through the ORM (**except for sudo mode**)."*
  (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/orm/models.py)
- **Inference —** Taken together, every mechanism reviewed in this section is
  an **application-layer permission check** (view filtering, `fields_get()`
  filtering, ORM `AccessError`, SQL domain-predicate filtering) enforced by
  Odoo's Python ORM above a plain, unencrypted PostgreSQL column. None of it is
  encryption-at-rest. A `sudo()`/superuser context, a direct-SQL code path, or
  DB/backup-level access all bypass it and expose the raw stored value.

### Real official examples: how Odoo's own core/business modules actually store third-party API credentials

Every concrete example found in official Odoo 19.0 source follows the **same
pattern**: a plain `fields.Char`, restricted by `groups='base.group_system'`,
**never** `password=True`, and **no encryption or hashing applied before
database storage**:

| Model | Field(s) | Mechanism (Official source-code fact) |
| --- | --- | --- |
| `ir.mail_server` | `smtp_pass` | `fields.Char(groups='base.group_system')`; no `password=True`; no crypto (https://raw.githubusercontent.com/odoo/odoo/19.0/odoo/addons/base/models/ir_mail_server.py) |
| `payment.provider` (Stripe) | `stripe_secret_key`, `stripe_webhook_secret` | Same pattern; `stripe_publishable_key` intentionally left unrestricted (meant to be public) (https://raw.githubusercontent.com/odoo/odoo/19.0/addons/payment_stripe/models/payment_provider.py) |
| `payment.provider` (Adyen) | `adyen_api_key`, `adyen_hmac_key`, `adyen_merchant_account` | Same pattern (all three carry `groups='base.group_system'`); `adyen_client_key` unrestricted (client-side use) (https://raw.githubusercontent.com/odoo/odoo/19.0/addons/payment_adyen/models/payment_provider.py) |
| `payment.provider` (Authorize.Net) | `authorize_transaction_key`, `authorize_signature_key` | Same pattern; `authorize_login`/`authorize_client_key` unrestricted (https://raw.githubusercontent.com/odoo/odoo/19.0/addons/payment_authorize/models/payment_provider.py) |
| `iap.account` | `account_token` | Auto-generated UUID hex, `fields.Char(groups='base.group_system')`; only hashed (`hashlib.sha1`) when transmitted to Odoo's own external IAP credit service — **the stored database column itself is plain text** (https://raw.githubusercontent.com/odoo/odoo/19.0/addons/iap/models/iap_account.py) |
| `auth.oauth.provider` | *(no `client_secret` field exists in this core model at all)* | Only `client_id` is stored, unrestricted; Odoo's native OAuth login flow does not require a server-side secret for this model (https://raw.githubusercontent.com/odoo/odoo/19.0/addons/auth_oauth/models/auth_oauth.py) |

- **Official source-code fact —** The base `payment.provider` model itself
  declares no generic secret/API-key field; it only imports an empty
  `SENSITIVE_KEYS` set (`addons/payment/const.py`) used to configure **log
  redaction** for a payment logger — provider submodules are expected to extend
  this set with their own field names so those values are scrubbed from logs.
  This is a **logging/audit-exposure mitigation**, not encryption.
  (https://raw.githubusercontent.com/odoo/odoo/19.0/addons/payment/models/payment_provider.py)
- **Inference —** This is a consistent, cross-module, repeated pattern (five
  independent provider/module examples), not an isolated anecdote: **Odoo's
  own core and business addons treat `groups='base.group_system'` as the
  standard protection for a third-party API secret, and do not apply
  field-level encryption to any of them.**

### Encryption-at-rest: infrastructure/hosting claim vs. application/field-level claim — clearly distinct

- **Fact (absence confirmed) —** None of the official 19.0 Odoo.sh
  administration pages (main page + all 9 subsections: Create a project,
  Branches, Builds, Settings, Online editor, Create a module, Advanced,
  Containers, Submodules, Frequent Technical Questions) or the Odoo Online
  administration page mention encryption at rest, disk encryption, or backup
  encryption anywhere.
  (https://www.odoo.com/documentation/19.0/administration/odoo_sh.html and
  subpages; https://www.odoo.com/documentation/19.0/administration/odoo_online.html)
- **Fact (official first-party corporate page, *not* a versioned
  `/documentation/19.0/` page) —** Odoo's first-party security page states
  that Odoo Cloud customer data is encrypted at rest with AES-256: *"All
  customer data (database content and stored files) is encrypted at rest,
  both in production and in backups with AES-256"* — stated under a section
  explicitly headed **"Odoo Cloud (the platform)."** **This is
  infrastructure/platform-level, not field-level ORM encryption** — it says
  nothing about field-level/per-column encryption inside the ORM/database
  schema. **Exact applicability across Odoo Online, Odoo.sh, and on-premise
  remains a hosting-scope question, not separately sourced or confirmed
  here:** the corporate page's own scope heading is the umbrella term "Odoo
  Cloud (the platform)," not a named product; the versioned Odoo.sh
  administration docs checked immediately above contain **no**
  encryption-at-rest statement of their own, so this corporate-page claim
  must **not** be read as confirming Odoo.sh coverage specifically (nor
  Odoo Online coverage specifically), and it says nothing about on-premise
  deployments at all. **Do not use this claim as a field-level or
  connector-level security guarantee.**
  (https://www.odoo.com/security)
- **Fact (same page) —** *"Customer passwords are protected with
  industry-standard PBKDF2+SHA512 encryption (salted + stretched for thousands
  of rounds)"* — this is specifically about **login-password hashing**
  (matches the `res.users` mechanism above), scoped to authentication
  credentials, not general data. The same page inconsistently calls the
  identical mechanism "hashing" elsewhere (its OWASP section: "Odoo uses
  industry-standard secure hashing for user passwords... to protect stored
  passwords") — a real terminology conflation on Odoo's own official page,
  worth flagging rather than repeating uncritically. (https://www.odoo.com/security)
- **Fact (official first-party corporate page, GDPR) —** The GDPR page's
  "Integrity and Confidentiality" section includes, as **illustrative
  compliance guidance directed at the customer/data-controller** ("Make sure
  your backup system is working, have proper security controls in place, use
  encryption to protect sensitive data such as passwords..."), a generic
  example — **not** a technical claim about what Odoo's own product implements
  at the database level. (https://www.odoo.com/gdpr)
- **Fact —** The official 19.0 External API reference's guidance on API keys
  is: *"Copy the key immediately and store it securely... Please refer to
  OWASP's Secrets Management Cheat Sheet for further guidance"* — **no
  Odoo-internal storage mechanism, module, or pattern is named or recommended**
  anywhere in this or any other official 19.0 developer-reference page checked
  this session.
  (https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
- **Fact —** The on-premise deployment doc's master `admin_passwd` (used only
  to gate database create/drop/restore operations from the web
  database-manager) is shown stored **hashed (PBKDF2)** in `odoo.conf` after a
  reset — but the same page's own configuration sample also shows
  `admin_passwd`/`db_password` in **plaintext**, and the reset flow has an
  explicit **transient plaintext state** before rehashing. This is a distinct,
  single-value, config-file mechanism unrelated to application data or
  connector credentials.
  (https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html)

## What is not confirmed

- Whether `ir.config_parameter`'s `_allow_sudo_commands = False` attribute has
  any bearing on confidentiality/encryption — its exact runtime semantics were
  not found documented anywhere in scope of this session (open question, not
  interpreted).
- Whether any non-core/OCA or Odoo Enterprise-only module implements genuine
  field-level encryption-at-rest for arbitrary `Char`/`Text` fields — out of
  scope (community modules are excluded as evidence per this task's hard
  rules; Enterprise-only source was not accessed this session). **This is a
  material gap, not a footnote: this document's conclusions are scoped to
  official Community/core Odoo 19 docs/source actually reviewed, and do not
  extend to Enterprise-only modules, third-party modules, custom
  application-side encryption, or external secret managers unless those are
  separately researched.**
- Whether Odoo's corporate "Odoo Cloud" AES-256 encrypted-at-rest claim maps
  onto Odoo Online, Odoo.sh, both, or neither, in the way the versioned
  administration docs would confirm — the corporate page's own scope is the
  umbrella term "Odoo Cloud (the platform)," and the versioned Odoo.sh/Odoo
  Online administration docs checked contain no encryption-at-rest statement
  of their own, so this mapping is an **open hosting-scope question, not
  confirmed either way for Odoo Online or Odoo.sh specifically**. The claim
  also says nothing about on-premise deployments, which are not addressed by
  that page or by the versioned administration docs checked.
- Whether any Odoo core mechanism provides secret **rotation** or
  **revocation** tooling beyond manually overwriting an
  `ir.config_parameter`/model field value — not found in any source reviewed
  this session (not asserted either way beyond what was checked).
- The exact reason Odoo's native `auth_oauth` provider model has no
  `client_secret` field (the plausible explanation — an implicit-flow-style
  login pattern not requiring one — is an inference from the field's absence
  in source, not confirmed against an official doc page this session).

## Odoo mechanisms reviewed

- **`fields.Char(password=True)` / view-architecture masking** — reviewed in
  full; confirmed to be (a) not a recognized ORM `Field`/`Char` constructor
  parameter at all under the default `_valid_field_parameter` behavior, and (b)
  actually implemented as a **view-arch XML attribute** (`<field
  password="1">`) consumed entirely by the JS web client for **display-only**
  masking, after the true value has already been delivered to the browser via
  `read()`. See "`password` is a view/UI attribute" above.
- **`ir.config_parameter`** — reviewed in full: plain `Char`/`Text` key-value
  storage, `group_system`-only ACL, no encryption, used by Odoo's own core for
  a generated secret-like value (`database.secret`) with no special protection
  beyond the standard ACL.
- **Access groups/ACLs** (`ir.model.access`, `ir.rule`, field `groups`) —
  reviewed in full: confirmed access-control-only (view/API/CRUD gating),
  explicitly not encryption, and explicitly bypassed by `sudo()`/superuser mode
  even at the field-`groups` level.
- **Odoo source examples of external API tokens** — found and reviewed five
  concrete, official examples (`ir.mail_server`, three payment providers,
  `iap.account`) plus one negative example (`auth_oauth` has no secret field);
  all five real secret-storing examples use the identical
  `groups='base.group_system'`-only pattern, none use `password=True`, none
  apply encryption.
- **Official encryption-at-rest mechanism** — **no official Odoo 19
  Community/core field-level or ORM encryption-at-rest mechanism was found in
  the official docs/source reviewed.** The only encryption-at-rest claim found
  anywhere is **infrastructure/platform-level** (Odoo's corporate security
  page: "Odoo Cloud" whole-disk/whole-DB/whole-backup AES-256), not a
  field-level/ORM mechanism, not documented as covering on-premise
  deployments, and not confirmed to specifically cover Odoo.sh or Odoo Online
  by the versioned administration docs (which contain no encryption-at-rest
  statement of their own). **Enterprise-only modules, third-party modules,
  custom application-side encryption, and external secret managers remain
  outside this evidence base unless separately researched** (not reviewed
  this session).

## Security interpretation

- **UI masking** — The `password` view-arch attribute (and the
  `PasswordField`/`CharField` web-client widgets) only change what is
  *rendered* in the browser. The true value has already left the server in the
  RPC response before masking is applied; this provides zero protection
  against a user with API/RPC access, a browser dev-tools inspection, or the
  widgets' own reveal-toggle mechanism.
- **Access control** — `ir.model.access`, `ir.rule`, and field-level `groups`
  are the real protective mechanism for who can read/write a value through the
  ORM/web client. This is meaningful, but it is **entirely bypassed by
  `sudo()`/superuser mode** (confirmed at the field-`groups` level, not just
  model/record level) and by any direct-SQL or non-ORM code path.
- **Database storage** — Every credential-like field found in official Odoo
  source (`ir.config_parameter.value`, `ir.mail_server.smtp_pass`, or any
  payment-provider secret field) is stored as a **plain, unencrypted
  PostgreSQL column value**. No transformation is applied before the
  `INSERT`/`UPDATE`.
- **Encryption-at-rest** — **No official Odoo 19 Community/core field-level or
  ORM encryption-at-rest mechanism was found in the official docs/source
  reviewed** (developer documentation or core source files). The only
  encryption-at-rest claim found anywhere is Odoo's first-party security page
  stating that **Odoo Cloud** customer data is encrypted at rest with
  AES-256 — this is **infrastructure/platform-level, not field-level ORM
  encryption**, and its exact applicability across Odoo Online, Odoo.sh, and
  on-premise is a hosting-scope question not separately confirmed here (see
  "What is not confirmed"); it is not a substitute for field-level protection
  of an individual secret value against another user/process with database
  access, and must not be used as a field-level or connector-level security
  guarantee. **Enterprise-only modules, third-party modules, custom
  application-side encryption, and external secret managers remain outside
  this evidence base unless separately researched.**
- **Audit/logging exposure** — The one concrete mitigation found for this risk
  is the payment module's `SENSITIVE_KEYS` log-redaction set (extended
  per-provider) — a real, but narrow, precedent: Odoo's own core explicitly
  treats "don't let the secret leak into logs" as a *separate* concern from
  storage/access-control, worth designing for deliberately rather than assuming
  logging is safe by default.
- **Backup/database-admin/superuser exposure** — This is the single largest
  confirmed gap: because storage is plain-column and access control is
  bypassed by `sudo()`/superuser mode, **any code path or person with
  database-admin, backup-file, or superuser/`sudo()` access sees the raw
  credential value**, regardless of field-level `groups`. Where Odoo's
  corporate-page "Odoo Cloud" infrastructure-level encryption-at-rest claim
  applies (hosting-scope not separately confirmed — see above), it mitigates
  *disk/backup-theft* exposure but not *database-admin/superuser-context*
  exposure, which is a separate threat model.

## Implications for Shopify connector

- A Shopify Admin API access token stored in a plain Char field, even one
  restricted with `groups='base.group_system'`, is **stored as plaintext in the
  database column** and is **readable by any code path that calls `sudo()`**
  (including background `ir.cron` jobs, which commonly run in an
  elevated/service context) and by anyone with direct database or backup
  access. This is **exactly the pattern every real official Odoo secret field
  uses today** (`smtp_pass`, Stripe/Adyen/Authorize.Net keys, IAP token) — it
  is Odoo's de facto standard, not a connector-specific shortcut, but it is
  **access control, not encryption**.
- DEC-004's existing posture ("masked storage, field-level `groups`,
  least-privilege scopes") is **fully consistent with, and matches, this de
  facto official pattern** — and, checking its text, DEC-004 never claims this
  constitutes encryption-at-rest; it says only "masked" (UI) and "`groups`"
  (access control), which this research confirms are the accurate terms and
  the ceiling of what plain Odoo ORM mechanisms provide.
- If genuine encryption-at-rest of the stored token value is required beyond
  what infrastructure-level disk encryption may provide (e.g. to protect
  against a database-admin-level or backup-file-level actor, or for
  on-premise deployments where no infrastructure encryption claim is
  documented at all), **no official Odoo 19 Community/core ORM/field
  mechanism was found in the official docs/source reviewed that provides
  it.** The realistic alternatives — relying on whichever hosting platform's
  own infrastructure encryption applies (Odoo's corporate "Odoo Cloud"
  AES-256 claim, whose exact Odoo Online/Odoo.sh/on-premise applicability is
  a hosting-scope question not separately confirmed here — do not treat it
  as a field-level or connector-level guarantee), a connector-designed
  application-side encryption layer (analogous to how `res.users.password`
  hashes rather than stores plaintext), or storing the secret outside Odoo
  entirely — are **design choices this document does not make**; see the
  decision proposal. **Evidence blocker is resolved for the official
  Community/core Odoo 19 sources reviewed; mechanism selection remains
  pending ChatGPT acceptance.**
- `ir.config_parameter` is **not** a stronger or more secure alternative to a
  normal model field for this purpose — it has identical plain-storage
  characteristics, plus a single shared `group_system` ACL for the entire
  table (no per-key access differentiation), which is *less* granular than a
  dedicated credential field with its own `groups=` value.
- Whatever storage mechanism is chosen, the payment-module
  `SENSITIVE_KEYS`-style log-redaction precedent should be treated as a
  **required**, not optional, companion measure — official Odoo code treats
  this as a distinct duty from storage/access-control.

## Open questions

1. Whether Odoo Enterprise, third-party modules, or a custom application-side
   encryption layer (not reviewed this session — out of scope) offer any
   field-level encryption-at-rest mechanism unavailable in the official
   Community/core Odoo 19 docs/source reviewed here.
2. The exact runtime semantics of `ir.config_parameter._allow_sudo_commands =
   False` and whether it has any confidentiality implication.
3. Whether Odoo's corporate "Odoo Cloud" AES-256 at-rest claim specifically
   covers Odoo Online, Odoo.sh, both, or neither, and whether it extends in
   practice to a customer's own on-premise deployment at all — the corporate
   page's own scoping heading is the umbrella term "Odoo Cloud (the
   platform)," not a named product, and this was not independently confirmed
   against any versioned technical doc (the versioned Odoo.sh/Odoo Online
   administration docs checked contain no encryption-at-rest statement of
   their own).
4. Whether a connector-designed application-side encryption/decryption layer
   (encrypting the token before writing to a `Char`/`Text` field, decrypting on
   use) should be evaluated as design material, given no official Odoo
   mechanism provides one out of the box — not decided here.
5. Rotation/revocation tooling and audit-metadata requirements for a future
   credential record — not addressed by any official mechanism reviewed and
   not decided here.
