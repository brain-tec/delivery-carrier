##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################


from odoo import fields, models
import ast


class StockPicking(models.Model):
    _inherit = "stock.picking"

    service_ids = fields.Many2many('picking.service')

    def button_validate(self):
        # Check Domain of Available Services
        services = self.env['shipment.service'].search([])
        product_product = self.env['product.product']
        picking_service = self.env['picking.service']
        for service in services:
            product_domain = service.product_domain
            products = product_product.search(ast.literal_eval(product_domain))
            if any(p_id in products.ids for p_id in self.move_ids_without_package.mapped('product_id').ids):
                # Don't add multiple times the same time of service
                if service not in self.service_ids.mapped('service_id'):
                    new_service = picking_service.create({
                        'service_id': service.id,
                        'attribute_id': service.available_attribute_ids[0].id,
                    })
                    self.service_ids |= new_service
        return super(StockPicking, self).button_validate()
