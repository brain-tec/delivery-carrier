##############################################################################
#
#    Copyright (c) 2022 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################

from odoo import models, fields


class ShipmentServiceAttribute(models.Model):
    _name = 'shipment.service.attribute'
    _rec_name = 'value'

    value = fields.Char(required=True)
    related_service_id = fields.Many2one('shipment.service')
