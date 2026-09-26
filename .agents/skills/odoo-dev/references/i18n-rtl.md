# English and Arabic (right-to-left)

The project languages are in `.odoo-harness/project.json` (default `en_US` and `ar_001`). In Odoo, Arabic is `ar_001` (ISO code `ar`, right-to-left) and its translations live in `i18n/ar.po` (`odoo/addons/base/data/res.lang.csv`).

## Making text translatable

- Python: `self.env._("Order %(name)s is locked", name=order.name)`. Put variables in named placeholders, never concatenate translated fragments, and don't translate at import time.
- JavaScript: `import { _t } from "@web/core/l10n/translation";` then `_t("Text")`.
- XML: view labels, strings, selection labels, menu and action names are exported automatically.
- Fields: `translate=True` on `Char`, `Text` and `Html` makes the stored content translatable per language (product names, descriptions). Labels (`string=`) are always translatable; they don't need it.

## Producing `ar.po`

1. `oh test my_module --keep` (after your last code change, so the database knows every new term).
2. `oh i18n my_module` regenerates `my_module/i18n/ar.po`, keeping existing translations, and prints how many entries are still untranslated. `--pot` also writes the template. It runs Odoo's `odoo-bin i18n export`.
3. Fill in every empty `msgstr`. For standard concepts, reuse the wording of Odoo's own Arabic translation of the related module: it's the `i18n/ar.po` file under the path printed by `oh src --where <module>`. Use the customer's glossary where one exists.
4. Re-run `oh test`, then check the Arabic screenshots.

Untranslated terms show up in English on Arabic screens; check the `oh shot` images for them.

## Right-to-left layout

- Odoo mirrors the web client for Arabic with rtlcss; `oh env` installs rtlcss locally so screenshots match. In custom SCSS, write direction-neutral styles where you can. rtlcss flips `left`/`right`; add `/*rtl:ignore*/` before a rule that must not flip, such as a logo position.
- Numbers, amounts and dates follow the language settings (Arabic in Odoo: `%d/%m/%Y` dates). Format with `t-field` or `t-options` widgets (monetary, date), not with manual `strftime`, so each language gets its own format.
- Mixed Arabic and Latin text (codes, references, emails) can reorder visually. Check it in the screenshots, and wrap such values in their own element where needed.
- PDF reports: render per partner language with `t-lang` (see `reports.md`). Check the final Arabic PDF on Odoo.sh; wkhtmltopdf may be missing locally.

## Pitfall: creating databases with Arabic

Creating a database with `--load-language ar_001` alone activates Arabic, leaves English inactive, and makes the admin user Arabic. Load `en_US,ar_001` together. `oh` does this for its databases.
