1.2.8 (05-Oct-2026):

- Added support for Metaobject Reference type metafields.

1.2.7 (16-Sep-2026):

- Fixed Shopify order import to log missing normal products and stop the affected order from being imported.
- Reduce api call from operation wizard.
- Improved collection management to align with Shopify latest collection rules, with enhanced conditions and a new Collection Items tab.

1.2.6 (11-Sep-2026):

- Keep your existing Warehouse and Stock Location on Shopify locations when confirming the instance again.
- Improved Shopify Marketplace User access rights with proper role-based permissions, allowing only the required Shopify operations and configurations.

1.2.5 (08-Sep-2026):

- Support bulk operations for Listing Export and Update when processing more than 3 listings.
- Fix an error shown while updating listings when a product was already removed from Shopify, and skip such a listing for the rest of the update.

1.2.4 (20-Aug-2026):

- Implemented Odoo return import during Shopify order sync.
- Fixed partial restocking and return processing for partially restocked returns.

1.2.3 (18-Aug-2026):

- Secure Shopify credentials, webhook HMAC, API retries, sync safety, access rights, and refund idempotency.

1.2.2 (13-Aug-2026):

- Fix group access for non-admin users.
- Fetch missing Shopify fraud analysis data for webhook-imported orders.

1.2.1 (04-Aug-2026):

- Added a help video to the operation popup.
- Implemented Shopify return creation from Odoo for already fulfilled orders.
- Updated the return workflow to match Shopify, so stock moves are created only when a return is approved or processed rather than when it is created.
- Update the migration script to prevent an Odoo server crash during a bulk category fetch, and to write product type, product category, and sales channel onto products when migrating to v19.
- Fix errors and warning messages raised during Odoo unit tests.

1.2.0 (24-Jul-2026):

- Fix an error during order processing by passing an empty `account.tax` recordset instead of a list.

1.1.10 (22-Jul-2026):

- Improve the refund error message for currency mismatches between Odoo and Shopify.
- Fix the unsupported auto-process payout popup shown in the Enterprise version.

1.1.9 (25-June-2026):

- Improve collection duplication, collection wizard messages, error messages, and instance selection for new collections.
- Mark orders as paid by capturing authorized payments.
- Improve refund flow with button visibility, auto-filled refund amount, and credit note validation.
- Enforce the `Go Live` safeguard for API requests on neutralized databases.

1.1.8 (17-June-2026)

- Fix the onboarding panel not displaying data correctly in dark mode.
- Added location-wise delivery order and stock move creation.
- Added multi-location return processing support.

1.1.7 (11-June-2026)

- Removed `Inventory Location Activation` and added custom fulfillment location handling.

1.1.6 (05-June-2026)

- Add `Collections` and `Catalogs` smart buttons to listings.
- Support multi-location fulfillment flow for Odoo pickings and stock moves.
- Add the `Generate Access Token` view.
- Prevent stock move creation errors when importing fulfilled Shopify orders for out-of-stock lot/serial-tracked products.
- Implemented a one-click `Sync to Shopify` button for direct listing updates from Odoo to Shopify.
- Implemented Shopify return management, covering return import, processing, restock handling, and synchronization between Shopify and Odoo.
- Added Shopify sales channel support for listing items.

1.1.5 (03-June-2026)

- Added support for importing and updating the Shopify catalog.

1.1.4 (01-June-2026)

- Implemented GraphQL queries for Shopify API version 2026-07.
- Added support for multiple languages in Shopify.

1.1.3 (20-May-2026)

- Fix incorrect data being written when a product is processed from a webhook.
- Added support for importing Shopify customer metafields into Odoo.
- Improved Shopify pagination handling and added timeout support for category taxonomy fetches.
- Implemented order metafield import from Shopify into Odoo.
- Fix sales channels not being fetched during collection import.
- Restructured the Shopify menu.
- Added the `Real-Time Price Sync to Shopify` setting for automatic price updates.

1.1.2 (11-May-2026)

- Implemented auto-reconcile payouts for Enterprise users only.
- Fix `Import Draft Product` when a date range is used.
- Allow the last export date for price and inventory to be changed from the operation wizard.
- Set the default sales channel action to `Publish`, remove deleted Shopify sales channels from Odoo, and improve logging for sales channel operations.
- Implemented `Skip Listing` to stop updates flowing between Odoo and Shopify.
- Sync country of origin and HS code in import/export listing operations.
- Add a `Group By` option and an active location label.
- Make Shopify sales channels instance-specific to prevent cross-instance conflicts in multi-instance setups.

1.1.1 (08-May-2026)

- Added metafield import and export for products and variants.

1.1.0 (07-May-2026)

- Raise a redirect warning with a dynamic error message that opens the matching instance form view.

1.0.10 (27-April-2026)

- Improved order import functionality to fetch orders based on the creation date when `Import Order After` is configured.
- When `Auto Sync Inventory Odoo to Shopify` is enabled in stock settings, product stock is automatically synced to Shopify on inventory changes.
- Migrate Shopify collections from the REST API to GraphQL.
- Added a quick onboarding panel for faster marketplace instance setup.

1.0.9 (17-April-2026)

- Apply country-based filtering for delivery carriers, prioritizing matches by destination country when carrier codes are shared.
- Migrated discount data from `Shopify Discount Amount` to `Marketplace Discount Amount`. The `Shopify Discount Amount` field has been removed.

1.0.8 (16-April-2026)

- Migrate `Import Inventory` from the REST API to GraphQL.

1.0.7 (14-April-2026)

- Create a to-do activity for Shopify risk orders.
- Added support for exporting stock across multiple locations to corresponding Shopify locations.
- Improved pickup order processing so items are active at the selected location before being transferred to the pickup location.
- Improved error handling with a clear message when an instance is confirmed with incorrect credentials.
- Remove the separate discount order line. The order discount is now applied to the Odoo discount field instead of creating a new sale order line.

1.0.6 (06-April-2026)

- Fix parent customer creation from the Shopify queue job.
- Fixed an import error caused by invalid `sys.exception` usage, and corrected the field visibility condition for the Shopify marketplace in the form view.
- Fixed the parent reference on partner records and included the partner type in the matching criteria for accurate identification.
- Sync listings from Shopify into the Odoo listing form view.
- Added quantity and price updates from Shopify listing items.

1.0.5 (31-March-2026)

- Added marketplace-specific image handling when adding products to listings.
- Fixed inventory double-counting by syncing the available quantity instead of the on-hand value.

1.0.4 (26-March-2026)

- Added `Mark as Picked Up` and `Ready for Pickup` buttons to the delivery order screen to update the Shopify pickup status.
- Migrated the Fulfillment Order API from REST to GraphQL.

1.0.3 (18-March-2026)

- Excluded third-party locations from inventory activation logic for multi-location Shopify products.
- Handle missing or empty values more safely to improve reliability.

1.0.2 (16-March-2026)

- Added a `Fetch Category` option to the `Category` menu to import categories directly from Shopify.
- Fixed the invoice line discount not updating correctly when a Shopify discount was applied.

1.0.1 (02-Dec-2025)

- Removed the `Shopify Checkout ID` field, which is deprecated in GraphQL.
- Added the `Shopify Payment ID` to the invoice payment register memo.
- Added a `Generate Access Token` option.
- Migrated the webhook REST API to GraphQL.
- Implemented a migration script to automatically assign sales channels to existing listings from older versions during the upgrade to v19.
- Implemented log redirection for better visibility of actions performed during `Export/Update Listing`.

1.0.0 (17-Nov-2025)

- Initial release for Odoo v19.
