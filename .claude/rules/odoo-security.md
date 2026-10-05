---
paths:
  - "**/security/**"
  - "**/controllers/**"
---

Access rights and controllers: read `.claude/skills/odoo-dev/references/security.md` before editing (access rows for every model after the XML that defines its groups, company record rules, narrow `sudo()`, controller `auth` and `type="jsonrpc"`, validated parameters). Each permission rule gets a test with the allowed user succeeding and the denied user getting `AccessError`.
