##############################################################################
#
#    Copyright (c) 2022 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################

from odoo import fields, models


class ShipmentService(models.Model):
    _name = "shipment.service"

    name = fields.Char(required=True)
    name_xsd = fields.Char("Name in the XSD Space", required=True)
    available_attribute_ids = fields.One2many(
        "shipment.service.attribute", "related_service_id"
    )
    product_domain = fields.Char(
        string="Product Domain",
        help="Domain that is applied over the products for this service",
    )
