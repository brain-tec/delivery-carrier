##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    street_no = fields.Char("Street No.")
