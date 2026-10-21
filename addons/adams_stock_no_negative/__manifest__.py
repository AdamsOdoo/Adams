{
    "name": "Adams Stock No Negative",
    "summary": "Block stock operations that would take on-hand quantities below zero",
    "description": """
Adams Stock No Negative
=======================

Validating a stock operation that would take a storable product below zero in an internal or
transit location is refused, with the product named in the message. This covers deliveries,
internal transfers, scrap, inventory adjustments, manufacturing consumption, Point of Sale
pickings and edits of done operations. The check is per product, location, lot/serial number,
package and owner, and holds when two users validate at the same time.

Not checked: consumables, partner and virtual locations, the shared inter-company transit
location, and the subcontracting locations of the Subcontracting app (components consumed by a
subcontracted receipt may go negative there, as in standard Odoo).

Inventory > Configuration > Settings > Operations:

- Bypass negative consumption prevention: allows negative stock for the whole company.
- Bypass negative consumption for Point of Sale (shown when Point of Sale is installed): allows it for Point of Sale
  orders only; ticked and read-only while the first bypass is on.

Both are off by default and only Settings administrators can change them.
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Inventory",
    "author": "Adams",
    "license": "LGPL-3",
    "depends": ["stock"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
