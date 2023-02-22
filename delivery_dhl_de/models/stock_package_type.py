##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################

from odoo import fields, models


class PackageType(models.Model):
    _inherit = "stock.package.type"

    package_carrier_type = fields.Selection(
        selection_add=[("dhl_de", "DHL DE")], ondelete={"dhl_de": "set default"}
    )
