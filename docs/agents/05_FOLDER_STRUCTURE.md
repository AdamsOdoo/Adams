# Module Folder Structure

## Complete Module Layout

```
addons/
├── adams_base/                          # Base module (existing)
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   ├── views/
│   ├── security/
│   └── data/
│
└── adams_shopify/                       # Shopify connector module
    ├── __init__.py                      # Root init — imports models, controllers, wizards
    ├── __manifest__.py                  # Module manifest (marketplace-ready)
    │
    ├── models/                          # Odoo models (Backend Developer owns)
    │   ├── __init__.py
    │   ├── shopify_backend.py           # shopify.backend — connection config, sync triggers
    │   ├── shopify_binding.py           # shopify.binding — abstract base for all bindings
    │   ├── shopify_product_binding.py   # shopify.product.binding — product↔Shopify link
    │   ├── shopify_variant_binding.py   # shopify.variant.binding — variant↔Shopify link
    │   ├── shopify_customer_binding.py  # shopify.customer.binding — customer↔Shopify link
    │   ├── shopify_order_binding.py     # shopify.order.binding — order↔Shopify link
    │   ├── shopify_inventory_binding.py # shopify.inventory.binding — inventory↔Shopify link
    │   ├── shopify_webhook_log.py       # shopify.webhook.log — webhook event log
    │   ├── shopify_sync_log.py          # shopify.sync.log — sync operation log
    │   ├── product_template.py          # Extends product.template with sync fields
    │   ├── product_product.py           # Extends product.product with sync fields
    │   ├── res_partner.py               # Extends res.partner with sync fields
    │   ├── sale_order.py                # Extends sale.order with Shopify reference
    │   └── stock_quant.py               # Extends stock.quant for inventory sync triggers
    │
    ├── shopify_api/                     # Shopify API layer (Shopify Agent owns)
    │   ├── __init__.py
    │   ├── client.py                    # GraphQL HTTP client with rate limiting
    │   ├── auth.py                      # Authentication helpers
    │   ├── queries/                     # GraphQL query strings
    │   │   ├── __init__.py
    │   │   ├── product_queries.py       # Product CRUD queries/mutations
    │   │   ├── customer_queries.py      # Customer CRUD queries/mutations
    │   │   ├── order_queries.py         # Order read queries
    │   │   ├── inventory_queries.py     # Inventory mutations
    │   │   └── common_fragments.py      # Shared GraphQL fragments
    │   ├── transformers/                # Data transformation Odoo↔Shopify
    │   │   ├── __init__.py
    │   │   ├── product_transformer.py   # Product data mapping
    │   │   ├── customer_transformer.py  # Customer data mapping
    │   │   ├── order_transformer.py     # Order data mapping
    │   │   └── inventory_transformer.py # Inventory data mapping
    │   └── pagination.py               # Cursor-based pagination helpers
    │
    ├── sync/                            # Sync engine (shared ownership)
    │   ├── __init__.py
    │   ├── exporter.py                  # Base export logic (Odoo→Shopify)
    │   ├── importer.py                  # Base import logic (Shopify→Odoo)
    │   ├── product_sync.py              # Product-specific sync orchestration
    │   ├── customer_sync.py             # Customer-specific sync orchestration
    │   ├── order_sync.py                # Order-specific sync orchestration
    │   ├── inventory_sync.py            # Inventory-specific sync orchestration
    │   └── checksum.py                  # Checksum computation for change detection
    │
    ├── controllers/                     # HTTP controllers (Shopify Agent owns)
    │   ├── __init__.py
    │   └── webhook.py                   # Shopify webhook receiver + HMAC verification
    │
    ├── wizards/                         # User-facing wizards (Backend Developer owns)
    │   ├── __init__.py
    │   ├── shopify_sync_wizard.py       # Manual sync trigger wizard
    │   └── shopify_import_wizard.py     # Bulk import wizard
    │
    ├── views/                           # XML views (Backend Developer owns)
    │   ├── shopify_backend_views.xml    # Backend configuration form/tree
    │   ├── shopify_binding_views.xml    # Binding list views (debug)
    │   ├── shopify_sync_log_views.xml   # Sync log views
    │   ├── shopify_webhook_log_views.xml# Webhook log views
    │   ├── product_template_views.xml   # Product form — Shopify tab
    │   ├── res_partner_views.xml        # Partner form — Shopify tab
    │   ├── sale_order_views.xml         # Sale order — Shopify reference
    │   └── shopify_menu.xml             # Menu structure
    │
    ├── security/                        # Access control (Backend Developer owns)
    │   ├── ir.model.access.csv          # Model access rights
    │   └── shopify_security.xml         # Security groups + record rules
    │
    ├── data/                            # Default data
    │   ├── shopify_cron.xml             # Scheduled sync cron jobs
    │   └── shopify_data.xml             # Default configuration data
    │
    ├── migrations/                      # Version migration scripts (DevOps owns)
    │   └── 18.0.1.1.0/
    │       ├── pre-migrate.py
    │       └── post-migrate.py
    │
    ├── tests/                           # Tests (Testing Agent owns)
    │   ├── __init__.py
    │   ├── common.py                    # Shared test setup (backend, fixtures)
    │   ├── test_backend.py              # Backend connection tests
    │   ├── test_product_sync.py         # Product sync tests
    │   ├── test_customer_sync.py        # Customer sync tests
    │   ├── test_order_sync.py           # Order sync tests
    │   ├── test_inventory_sync.py       # Inventory sync tests
    │   ├── test_webhook.py              # Webhook controller tests
    │   ├── test_idempotency.py          # Cross-entity idempotency tests
    │   ├── test_error_handling.py       # Error scenario tests
    │   └── fixtures/                    # Mock API responses
    │       ├── shopify_product.json
    │       ├── shopify_customer.json
    │       ├── shopify_order.json
    │       ├── shopify_inventory.json
    │       ├── shopify_webhook_product.json
    │       └── shopify_error_responses.json
    │
    ├── static/                          # Static assets
    │   └── description/
    │       ├── icon.png                 # Module icon (128x128)
    │       ├── banner.png               # Marketplace banner
    │       └── screenshots/
    │           ├── 01_backend_config.png
    │           ├── 02_product_sync.png
    │           └── 03_sync_log.png
    │
    ├── i18n/                            # Translations
    │   └── adams_shopify.pot            # Translation template
    │
    └── README.rst                       # Marketplace description (OCA format)
```

## File Ownership Matrix

| Directory | Primary Owner | Secondary |
|-----------|--------------|-----------|
| models/ | Odoo Backend Developer | Technical Architect (design) |
| shopify_api/ | Shopify Integration Agent | Technical Architect (design) |
| sync/ | Both Developers | Technical Architect (design) |
| controllers/ | Shopify Integration Agent | — |
| wizards/ | Odoo Backend Developer | — |
| views/ | Odoo Backend Developer | — |
| security/ | Odoo Backend Developer | Technical Architect (design) |
| data/ | Odoo Backend Developer | DevOps Agent |
| tests/ | Testing Agent | — |
| migrations/ | DevOps Agent | — |
| static/ | DevOps Agent | — |
| __manifest__.py | DevOps Agent | — |

## Init Chain

### addons/adams_shopify/__init__.py
```python
from . import models
from . import controllers
from . import wizards
```

### addons/adams_shopify/models/__init__.py
```python
from . import shopify_backend
from . import shopify_binding
from . import shopify_product_binding
from . import shopify_variant_binding
from . import shopify_customer_binding
from . import shopify_order_binding
from . import shopify_inventory_binding
from . import shopify_webhook_log
from . import shopify_sync_log
from . import product_template
from . import product_product
from . import res_partner
from . import sale_order
from . import stock_quant
```

### addons/adams_shopify/controllers/__init__.py
```python
from . import webhook
```

### addons/adams_shopify/wizards/__init__.py
```python
from . import shopify_sync_wizard
from . import shopify_import_wizard
```
