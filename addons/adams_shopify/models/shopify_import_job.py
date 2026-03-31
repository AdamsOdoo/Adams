import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ShopifyImportJob(models.Model):
    _name = 'shopify.import.job'
    _description = 'Shopify Background Import Job'
    _order = 'create_date desc'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    entity = fields.Selection([
        ('product', 'Products'),
        ('customer', 'Customers'),
        ('order', 'Orders'),
    ], required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], default='pending', index=True)
    total_pages = fields.Integer('Total Pages', default=0)
    processed_pages = fields.Integer('Processed Pages', default=0)
    total_records = fields.Integer('Total Records', default=0)
    success_count = fields.Integer(default=0)
    error_count = fields.Integer(default=0)
    skipped_count = fields.Integer(default=0)
    progress = fields.Float('Progress (%)', compute='_compute_progress')
    cursor = fields.Char(
        'Pagination Cursor',
        help="Shopify GraphQL cursor for the next page.",
    )
    page_size = fields.Integer(default=50)
    error_details = fields.Text()
    started_at = fields.Datetime()
    finished_at = fields.Datetime()

    @api.depends('total_pages', 'processed_pages')
    def _compute_progress(self):
        for rec in self:
            if rec.total_pages > 0:
                rec.progress = (rec.processed_pages / rec.total_pages) * 100
            else:
                rec.progress = 0.0

    def action_cancel(self):
        """Cancel a pending or running job."""
        for job in self:
            if job.state in ('pending', 'running'):
                job.state = 'cancelled'

    @api.model
    def _cron_process_import_jobs(self):
        """Process one page of each pending/running import job."""
        jobs = self.search([
            ('state', 'in', ['pending', 'running']),
        ], order='create_date asc')

        for job in jobs:
            try:
                if job.state == 'pending':
                    job.write({
                        'state': 'running',
                        'started_at': fields.Datetime.now(),
                    })

                has_more = job._process_next_page()
                if not has_more:
                    job.write({
                        'state': 'done',
                        'finished_at': fields.Datetime.now(),
                    })
                    job.backend_id.last_sync_date = fields.Datetime.now()
                    _logger.info(
                        "Import job %s complete: %d success, %d errors, %d skipped",
                        job.id, job.success_count, job.error_count, job.skipped_count,
                    )

            except Exception as e:
                _logger.exception("Import job %s failed: %s", job.id, e)
                job.write({
                    'state': 'error',
                    'error_details': str(e),
                    'finished_at': fields.Datetime.now(),
                })
            # Commit per job to prevent one failure from rolling back others
            self.env.cr.commit()  # noqa: E501

    def _process_next_page(self):
        """Fetch and process the next page of data. Returns True if more pages exist."""
        self.ensure_one()
        from ..shopify_api.client import ShopifyClient

        client = ShopifyClient(self.backend_id)
        entity = self.entity

        if entity == 'product':
            return self._process_product_page(client)
        elif entity == 'customer':
            return self._process_customer_page(client)
        elif entity == 'order':
            return self._process_order_page(client)
        return False

    def _process_product_page(self, client):
        from ..shopify_api.queries.product import FETCH_PRODUCTS
        from ..sync.product_sync import ProductImporter

        variables = {'first': self.page_size}
        if self.cursor:
            variables['after'] = self.cursor

        body = client.execute(FETCH_PRODUCTS, variables, estimated_cost=12)
        data = body.get('data', {}).get('products', {})
        edges = data.get('edges', [])
        page_info = data.get('pageInfo', {})

        importer = ProductImporter(
            self.env.with_company(self.backend_id.company_id),
            self.backend_id,
        )

        nodes = [edge.get('node', {}) for edge in edges]
        success, errors, skipped = importer.import_batch(nodes)

        self._update_progress(success, errors, skipped, page_info)
        return page_info.get('hasNextPage', False)

    def _process_customer_page(self, client):
        from ..shopify_api.queries.customer import FETCH_CUSTOMERS
        from ..sync.customer_sync import CustomerImporter

        variables = {'first': self.page_size}
        if self.cursor:
            variables['after'] = self.cursor

        body = client.execute(FETCH_CUSTOMERS, variables, estimated_cost=12)
        data = body.get('data', {}).get('customers', {})
        edges = data.get('edges', [])
        page_info = data.get('pageInfo', {})

        importer = CustomerImporter(
            self.env.with_company(self.backend_id.company_id),
            self.backend_id,
        )

        nodes = [edge.get('node', {}) for edge in edges]
        success, errors, skipped = importer.import_batch(nodes)

        self._update_progress(success, errors, skipped, page_info)
        return page_info.get('hasNextPage', False)

    def _process_order_page(self, client):
        from ..shopify_api.queries.order import FETCH_ORDERS
        from ..sync.order_sync import OrderImporter

        variables = {'first': min(self.page_size, 50)}
        if self.cursor:
            variables['after'] = self.cursor

        body = client.execute(FETCH_ORDERS, variables, estimated_cost=20)
        data = body.get('data', {}).get('orders', {})
        edges = data.get('edges', [])
        page_info = data.get('pageInfo', {})

        importer = OrderImporter(
            self.env.with_company(self.backend_id.company_id),
            self.backend_id,
        )

        nodes = [edge.get('node', {}) for edge in edges]
        success, errors, skipped = importer.import_batch(nodes)

        self._update_progress(success, errors, skipped, page_info)
        return page_info.get('hasNextPage', False)

    def _update_progress(self, success, errors, skipped, page_info):
        """Update job progress after processing a page."""
        vals = {
            'processed_pages': self.processed_pages + 1,
            'success_count': self.success_count + success,
            'error_count': self.error_count + errors,
            'skipped_count': self.skipped_count + skipped,
            'total_records': self.total_records + success + errors + skipped,
        }
        if page_info.get('hasNextPage') and page_info.get('endCursor'):
            vals['cursor'] = page_info['endCursor']
        else:
            vals['cursor'] = False

        self.write(vals)
