##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################

from logging import getLogger

from odoo import SUPERUSER_ID, _, api, fields, models, registry
from odoo.exceptions import UserError

_logger = getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    has_errors_address_dhl = fields.Boolean(
        "Has the address errors according to DHL?", readonly=True
    )
    feedback_validation_address_dhl = fields.Char(
        "Feedback from DHL about the address", readonly=True
    )

    def action_confirm(self):
        for sale in self:
            if sale.carrier_id and sale.carrier_id.allows_dhl_validation():
                (
                    is_address_valid,
                    feedback_validation_address_dhl,
                ) = sale.carrier_id.dhl_validation(None, sale)

                so_vals = {
                    "has_errors_address_dhl": True,
                    "feedback_validation_address_dhl": feedback_validation_address_dhl,
                }

                if not is_address_valid:
                    if not self.env.context.get("propagate_errors"):
                        # When the action_confirm() is called from several
                        # places, each of them logging their own errors and
                        # raising their own exceptions, we end up with an
                        # unrecoverable concurrent-access because of the use
                        # of several cursors.
                        # So since we know when we are going to have this
                        # situation, we pass as context the flag
                        # 'propagate_errors' to indicate that no errors have
                        # to be written on the object *now*, that errors will
                        # be written *after* and that for the moment we just
                        # have to raise.
                        with registry(self.env.cr.dbname).cursor() as new_cr:
                            env = api.Environment(
                                new_cr, SUPERUSER_ID, self.env.context
                            )
                            sale.with_env(env).write(so_vals)
                    raise UserError(
                        _("According to DHL the address is not valid: %s")
                        % feedback_validation_address_dhl
                    )
                else:
                    sale.write(
                        {
                            "has_errors_address_dhl": False,
                            "feedback_validation_address_dhl": None,
                        }
                    )
        return super(SaleOrder, self).action_confirm()
