# Uninstall and credential revocation

Uninstall is deliberately fail-closed.

1. Resolve all Needs Attention and uncertain mutation attempts.
2. Run `Prepare webhook uninstall`. It performs a fresh subscription read and queues exact-GID deletion through the existing Layer-2 mutation/reconciliation path.
3. Wait until expected/registered subscriptions are retired and no webhook work is active.
4. Disconnect every store and wait for business jobs to reach terminal states.
5. Remove local credentials through the supported lifecycle. Do not query or export their stored value.
6. In Shopify Admin, rotate/revoke the custom-app token or client secret and, if no longer used, delete the merchant-managed custom app. Local uninstall cannot prove merchant-side revocation.
7. Uninstall webhook/domain addons, then core. The hooks refuse removal while subscriptions, credentials, active work, or unresolved uncertain evidence remain.
8. Retain the database backup according to the merchant's audit/data policy, recognizing that protected credentials were plaintext at rest.

Never force-drop connector tables to bypass an uninstall refusal. The refusal identifies evidence that must be reconciled or retained.
