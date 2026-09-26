# Odoo v19 Technical Reference for Adams Shopify Connector

> Sources: [Odoo 19 Release Notes](https://www.odoo.com/odoo-19-release-notes), [Nalios v19 Framework](https://www.nalios.com/en/blog/what-s-new-in-odoo-6/odoo-19-python-framework-what-s-new-in-v19-118), [Odoo v19 Documentation](https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html)

---

## 1. ORM Changes Relevant to Connector Development

### Performance Improvements (30-40% gains)
- **New query planner**: Reduces DB round-trips by up to 40%. Our batch sync operations benefit directly.
- **Batch prefetching**: Related fields loaded in a single query. Use `mapped()` and field prefetch for binding traversals.
- **Computed field caching**: Tiered in-memory + database cache. Sync checksums can leverage this.
- **Binary field lazy loading**: `image_1920` won't load unless accessed. Good for product sync performance.
- **Module loading 30-50% faster**: Faster install/update cycles during development and deployment.

### New Constraint & Index API
```python
# v19 style — use models.Constraint() and models.Index()
class ShopifyProductBinding(models.Model):
    _name = 'shopify.product.binding'

    # Old style (still works but deprecated pattern)
    _sql_constraints = [
        ('unique_binding', 'UNIQUE(backend_id, shopify_id)',
         'Binding already exists for this Shopify ID.')
    ]

    # v19 preferred: explicit index creation
    # Use models.Index() for frequently queried fields
    # Index on (backend_id, shopify_id) for fast binding lookups
    # Index on (backend_id, sync_status) for batch status queries
```

### Field Access Changes
- `prefetch=True` parameter available on field definitions for explicit prefetch control
- Field caching methods improved — use `invalidate_model()` for cache invalidation in concurrent scenarios
- `config.py` cleanup — check for any deprecated config patterns

### Key ORM Methods for Connector
```python
# Batch create (v19 optimized — single INSERT)
bindings = self.env['shopify.product.binding'].create([
    {'backend_id': 1, 'shopify_id': 'gid://shopify/Product/1', 'odoo_id': p.id}
    for p in products
])

# Batch write (v19 optimized)
bindings.write({'sync_status': 'synced', 'last_sync_date': fields.Datetime.now()})

# Prefetch for avoiding N+1
bindings = self.env['shopify.product.binding'].search([('backend_id', '=', backend_id)])
bindings.mapped('odoo_id')  # Triggers prefetch for all odoo_id in single query
for binding in bindings:
    product = binding.odoo_id  # Served from cache

# Savepoint for safe API calls
with self.env.cr.savepoint():
    binding.write({'shopify_id': new_shopify_id})
    # If outer transaction rolls back, this savepoint can be preserved

# exists() for safe record checks (bypasses cache)
if not binding.exists():
    # Record was deleted concurrently
    pass

# flush() and invalidate for multi-process consistency
self.env['shopify.product.binding'].flush_model()
self.env['shopify.product.binding'].invalidate_model()
```

---

## 2. Module Manifest Format (v19 / Apps Store)

### Required Fields for Marketplace Submission
```python
{
    'name': 'Adams Shopify Connector',                  # Max 25 chars recommended
    'version': '19.0.1.0.0',                            # {odoo_version}.{major}.{minor}.{patch}
    'category': 'Sales/Sales',                           # Odoo category taxonomy
    'summary': 'Sync products, orders, customers and inventory with Shopify',
    'description': '',                                   # Use README.rst instead
    'author': 'Adams',
    'website': 'https://github.com/adamsodoo/adams',
    'license': 'LGPL-3',                                # LGPL-3, AGPL-3, OPL-1 for paid
    'depends': [
        'adams_base',
        'product',
        'sale_management',
        'stock',
        'contacts',
    ],
    'external_dependencies': {
        'python': ['requests'],                          # pip packages
    },
    'data': [
        'security/shopify_security.xml',                 # Groups first
        'security/ir.model.access.csv',                  # ACLs second
        'data/shopify_cron.xml',                         # Cron jobs
        'data/shopify_data.xml',                         # Default data
        'views/shopify_backend_views.xml',
        'views/shopify_binding_views.xml',
        'views/shopify_sync_log_views.xml',
        'views/shopify_dashboard_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/shopify_menu.xml',                        # Menu last
        'wizards/shopify_sync_wizard_views.xml',
    ],
    'demo': [],
    'assets': {},                                        # v19 OWL assets if needed
    'installable': True,
    'application': True,                                 # Shows as app in Apps menu
    'auto_install': False,
    'images': ['static/description/banner.png'],         # Marketplace banner
    'price': 0,                                          # Set for paid apps (EUR)
    'currency': 'EUR',
    'live_test_url': '',                                 # Demo instance URL
}
```

### Marketplace Submission Rules
- Module name max 25 chars in `name` field
- `version` must include Odoo version prefix (19.0.x.x.x)
- Bump version for every schema change requiring `--update`
- License: `LGPL-3` for free modules, `OPL-1` for proprietary/paid
- 90 days free support included with Odoo Apps Store purchase
- `README.rst` (not .md) is the marketplace description format
- `static/description/icon.png` — 128x128 module icon
- `static/description/banner.png` — marketplace banner
- Screenshots in `static/description/`
- No external API keys required during install (must work with test data)
- Must install cleanly on fresh database with dependencies satisfied
- No `sudo()` without justification in review
- No raw SQL without justification

---

## 3. Security Model

### Groups Pattern
```xml
<!-- security/shopify_security.xml -->
<odoo>
    <record id="module_category_shopify" model="ir.module.category">
        <field name="name">Shopify</field>
        <field name="sequence">100</field>
    </record>

    <record id="group_shopify_user" model="res.groups">
        <field name="name">User</field>
        <field name="category_id" ref="module_category_shopify"/>
        <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <record id="group_shopify_manager" model="res.groups">
        <field name="name">Manager</field>
        <field name="category_id" ref="module_category_shopify"/>
        <field name="implied_ids" eval="[(4, ref('group_shopify_user'))]"/>
    </record>
</odoo>
```

### Access Rights (ir.model.access.csv)
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_shopify_backend_user,shopify.backend.user,model_shopify_backend,group_shopify_user,1,0,0,0
access_shopify_backend_manager,shopify.backend.manager,model_shopify_backend,group_shopify_manager,1,1,1,0
access_shopify_backend_admin,shopify.backend.admin,model_shopify_backend,base.group_system,1,1,1,1
access_shopify_product_binding_user,shopify.product.binding.user,model_shopify_product_binding,group_shopify_user,1,0,0,0
access_shopify_product_binding_manager,shopify.product.binding.manager,model_shopify_product_binding,group_shopify_manager,1,1,1,0
access_shopify_sync_log_user,shopify.sync.log.user,model_shopify_sync_log,group_shopify_user,1,0,0,0
access_shopify_sync_log_manager,shopify.sync.log.manager,model_shopify_sync_log,group_shopify_manager,1,1,0,0
```

### Record Rules (Multi-Company Isolation)
```xml
<record id="shopify_backend_company_rule" model="ir.rule">
    <field name="name">Shopify Backend: multi-company</field>
    <field name="model_id" ref="model_shopify_backend"/>
    <field name="domain_force">[
        '|', ('company_id', '=', False),
        ('company_id', 'in', company_ids)
    ]</field>
</record>
```

### Multi-Company Best Practice (v19)
```python
class ShopifyBackend(models.Model):
    _name = 'shopify.backend'
    _check_company_auto = True  # v19: auto-check company consistency on relational fields

    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company
    )

    # All relational fields to company-scoped models get auto-checked
    warehouse_id = fields.Many2one(
        'stock.warehouse', check_company=True,
        default=lambda self: self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
    )
```

### Field-Level Security
```python
access_token = fields.Char(
    'Access Token', required=True,
    groups='base.group_system',  # Only system admins can see/edit
)
webhook_secret = fields.Char(
    'Webhook Secret',
    groups='base.group_system',
)
```

---

## 4. HTTP Controllers (Webhook Endpoints)

### v19 Controller Pattern
```python
import hmac
import hashlib
import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class ShopifyWebhookController(http.Controller):

    @http.route(
        '/shopify/webhook/<int:backend_id>',
        type='json',           # Parses JSON body automatically
        auth='none',           # No Odoo session required
        methods=['POST'],
        csrf=False,            # Webhooks can't include CSRF token
    )
    def handle_webhook(self, backend_id, **kwargs):
        """Receive and enqueue Shopify webhook events."""
        # 1. Get raw body for HMAC verification
        raw_body = request.httprequest.get_data()
        headers = request.httprequest.headers

        # 2. Verify HMAC
        hmac_header = headers.get('X-Shopify-Hmac-Sha256', '')
        topic = headers.get('X-Shopify-Topic', '')
        webhook_id = headers.get('X-Shopify-Webhook-Id', '')

        backend = request.env['shopify.backend'].sudo().browse(backend_id)
        if not backend.exists():
            return {'status': 'error', 'message': 'Unknown backend'}

        if not self._verify_hmac(raw_body, hmac_header, backend.webhook_secret):
            _logger.warning("Shopify webhook HMAC verification failed for backend %s", backend_id)
            # Return 401 via raising
            return {'status': 'unauthorized'}

        # 3. Dedup by webhook_id
        # 4. Parse and enqueue
        # 5. Return 200 (implicit with type='json')
        return {'status': 'ok'}

    def _verify_hmac(self, raw_body, hmac_header, secret):
        if not secret:
            return False
        computed = hmac.new(
            secret.encode('utf-8'),
            raw_body,
            hashlib.sha256,
        ).digest()
        import base64
        computed_b64 = base64.b64encode(computed).decode('utf-8')
        return hmac.compare_digest(computed_b64, hmac_header)
```

---

## 5. Cron Jobs (Scheduled Actions)

### v19 Cron Pattern
```xml
<!-- data/shopify_cron.xml -->
<odoo noupdate="1">
    <record id="ir_cron_shopify_sync_products" model="ir.cron">
        <field name="name">Shopify: Sync Products</field>
        <field name="model_id" ref="model_shopify_backend"/>
        <field name="state">code</field>
        <field name="code">model._cron_sync_products()</field>
        <field name="interval_number">15</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active" eval="True"/>
        <field name="doall" eval="False"/>
    </record>

    <record id="ir_cron_shopify_sync_orders" model="ir.cron">
        <field name="name">Shopify: Import Orders</field>
        <field name="model_id" ref="model_shopify_backend"/>
        <field name="state">code</field>
        <field name="code">model._cron_import_orders()</field>
        <field name="interval_number">5</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active" eval="True"/>
    </record>

    <record id="ir_cron_shopify_sync_inventory" model="ir.cron">
        <field name="name">Shopify: Push Inventory</field>
        <field name="model_id" ref="model_shopify_backend"/>
        <field name="state">code</field>
        <field name="code">model._cron_sync_inventory()</field>
        <field name="interval_number">10</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active" eval="True"/>
    </record>

    <record id="ir_cron_shopify_process_webhooks" model="ir.cron">
        <field name="name">Shopify: Process Pending Webhooks</field>
        <field name="model_id" ref="model_shopify_webhook_log"/>
        <field name="state">code</field>
        <field name="code">model._cron_process_pending()</field>
        <field name="interval_number">1</field>
        <field name="interval_type">minutes</field>
        <field name="numbercall">-1</field>
        <field name="active" eval="True"/>
    </record>
</odoo>
```

### Odoo.sh Cron Constraints
- Workers are limited based on plan (typically 2-4 workers)
- Long-running crons block workers — keep cron execution under 5 minutes
- Use `self.env.cr.commit()` between batches to release locks
- Use `try/except` around each batch to prevent full cron failure

---

## 6. Odoo.sh Deployment Specifics

### Environment Setup
- Python packages via `requirements.txt` in repo root (NOT in module)
- No system-level dependencies (no `apt-get`)
- Environment variables via Odoo.sh admin panel (for secrets)
- Custom addons in `addons/` directory

### Worker Limits
| Plan | Workers | Cron Workers |
|------|---------|-------------|
| Starter | 2 | 1 |
| Standard | 4 | 1 |
| Custom | Configurable | Configurable |

### Best Practices for Odoo.sh
```python
# Use ir.config_parameter for non-secret config
# (secrets should use Odoo.sh env vars or encrypted Char fields)

# Access env var:
import os
shopify_secret = os.environ.get('SHOPIFY_WEBHOOK_SECRET', '')

# OR use Odoo system parameters
self.env['ir.config_parameter'].sudo().get_param('adams_shopify.webhook_secret')
```

### Logging
```python
import logging
_logger = logging.getLogger(__name__)

# Odoo.sh shows logs in web interface
# Use appropriate levels:
_logger.debug("Processing product %s", product.id)       # Dev only
_logger.info("Exported %d products to Shopify", count)    # Normal operations
_logger.warning("Rate limited, backing off %ds", delay)   # Recoverable issues
_logger.error("Failed to export product %s: %s", pid, e)  # Errors needing attention
```

---

## 7. Key Odoo v19 References

| Topic | URL |
|-------|-----|
| Module Manifest | https://www.odoo.com/documentation/19.0/developer/reference/backend/module.html |
| ORM Reference | https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html |
| Security | https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html |
| Multi-Company | https://www.odoo.com/documentation/19.0/developer/howtos/company.html |
| HTTP Controllers | https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html |
| Testing | https://www.odoo.com/documentation/19.0/developer/reference/backend/testing.html |
| Webhooks (Studio) | https://www.odoo.com/documentation/19.0/applications/studio/automated_actions/webhooks.html |
| Apps Store Guidelines | https://apps.odoo.com/apps/vendor-guidelines |
| Release Notes | https://www.odoo.com/odoo-19-release-notes |
| v19 Python Framework | https://www.nalios.com/en/blog/what-s-new-in-odoo-6/odoo-19-python-framework-what-s-new-in-v19-118 |
