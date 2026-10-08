from odoo import api, models
from odoo.exceptions import UserError


class PosSalesReportPdf(models.AbstractModel):
    _name = 'report.adams_pos_sales_report.report_pos_sales'
    _description = 'POS Sales Report (PDF)'

    @api.model
    def _get_report_values(self, docids, data=None):
        # The report URL can be called directly: validate again, as the current user.
        if not data:
            raise UserError(self.env._("Print the sales report from Point of Sale > Reporting > Sales Report."))
        Report = self.env['report.pos.order']
        options = Report._psr_options(
            data.get('domain'), data.get('groupby'), data.get('columns'), data.get('mode'), data.get('filters'),
        )
        return {
            'doc_ids': [],
            'doc_model': 'report.pos.order',
            'docs': Report,
            **Report._psr_report_data(options),
        }
