from odoo import fields, models


class PackageType(models.Model):
    _inherit = "stock.package.type"

    package_carrier_type = fields.Selection(
        selection_add=[("dhl_de", "DHL DE")], ondelete={"dhl_de": "set default"}
    )
