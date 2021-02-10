from odoo import models, fields, api, _
from odoo.exceptions import UserError


import logging
_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    """ Add service group """

    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[("dhl_de", "DHL DE")])

    dhl_de_endpoint_url = fields.Char(string="Endpoint URL", default="https://cig.dhl.de/services/production/soap",
                                      required=True)
    dhl_de_user_id = fields.Char("DHL UserId", copy=False, help="When use the sandbox account developer id use as "
                                                                "the userId.When use the live account application "
                                                                "id use as the userId.")
    dhl_de_password = fields.Char("DHL Password", copy=False, help="When use the sandbox account developer portal "
                                                                   "password use to as the password.When use the "
                                                                   "live account application token use to as the "
                                                                   "password.")

    dhl_de_ekp_no = fields.Char("EKP Number", copy=False, help="The EKP number sent to you by DHL and it must be "
                                                               "maximum 10 digit allow.")

    @api.onchange("prod_environment")
    def onchange_prod_environment(self):
        """
        Auto change the end point url following the environment
        - Prod: https://cig.dhl.de/services/production/soap"
        - Test: https://cig.dhl.de/services/sandbox/soap
        """
        for carrier in self:
            if carrier.prod_environment:
                carrier.dhl_de_endpoint_url = "https://cig.dhl.de/services/production/soap"
            else:
                carrier.dhl_de_endpoint_url = "https://cig.dhl.de/services/sandbox/soap"

    def dhl_de_get_tracking_link(self, picking):
        raise UserError(_("This feature is under development"))

    def dhl_de_cancel_shipment(self, pickings):
        raise UserError(_("This feature is under development"))

    def dhl_de_rate_shipment(self, order):
        self.ensure_one()
        delivery_product_price = self.product_id and self.product_id.lst_price or 0
        return {
            "success": True,
            "price": delivery_product_price,
            "error_message": False,
            "warning_message": False,
        }

    def dhl_de_send_shipping(self, pickings):
        """
        It will generate the labels for all the packages of the picking.
        Packages are mandatory in this case
        """
        raise UserError(_("This feature is under development"))
