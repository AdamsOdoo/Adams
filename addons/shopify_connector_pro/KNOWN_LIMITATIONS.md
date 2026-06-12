# Known Limitations

Shopify Connector Pro Ultimate Edition is designed to make sync issues visible and actionable. Some edge cases may still require administrator review, especially during initial setup, historical imports, or unusual accounting/tax configurations.

## Merchant-Facing Notes

- Large historical backfills should be planned and monitored so API throttling, tax mappings, and reconciliation results can be reviewed safely.
- Accurate taxes, currencies, products, payment methods, and journals depend on completed setup and validated mappings.
- If Shopify or Odoo data is missing, archived, deleted, or inconsistent, the connector should surface the issue for review rather than silently guessing.
- Advanced or uncommon workflows may require feature flags, configuration review, or staged rollout before go-live.

## Where to Look

- User guidance: `doc/USER_GUIDE.md`
- Troubleshooting guidance: `doc/TROUBLESHOOTING.md`

Internal engineering triage details live outside the shipped addon documentation in `docs/architecture/KNOWN_LIMITATIONS.md`.
