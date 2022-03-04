##############################################################################
#
#    Copyright (c) 2022 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################

from odoo import models, fields


class PickingService(models.Model):
    _name = 'picking.service'

    service_id = fields.Many2one('shipment.service', required=True)
    attribute_id = fields.Many2one('shipment.service.attribute')
