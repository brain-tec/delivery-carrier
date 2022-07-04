##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################

from logging import getLogger

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    show_dhl_label_button = fields.Boolean(compute="_compute_show_dhl_label_button")
    dhl_de_picking = fields.Boolean(compute="_compute_dhl_de_picking")
    has_errors_address_dhl = fields.Boolean(
        "Has the address errors according to DHL?", default=False, readonly=True
    )
    feedback_validation_address_dhl = fields.Char(
        "Feedback from DHL about the address", readonly=True
    )
    dhl_delivery_address_validation = fields.Boolean()

    def _compute_dhl_de_picking(self):
        for record in self:
            if record.carrier_id and record.carrier_id.delivery_type == "dhl_de":
                record.dhl_de_picking = True
            else:
                record.dhl_de_picking = False

    @api.depends("carrier_tracking_ref", "carrier_id", "carrier_id.dhl_de_label_format")
    def _compute_show_dhl_label_button(self):
        for sp in self:
            att = sp.get_dhl_attachment()
            sp.show_dhl_label_button = bool(att)

    def get_dhl_attachment(self):
        attachments = self.env["ir.attachment"]
        if self.carrier_tracking_ref:
            for ref in self.carrier_tracking_ref.split(","):
                label_format = self.carrier_id.dhl_de_label_format
                attachment_name = "DHL Label-{}.{}".format(ref, label_format)
                attachments += self.env["ir.attachment"].search(
                    [
                        ("name", "=", attachment_name),
                        ("res_model", "=", self._name),
                        ("res_id", "=", self.id),
                    ],
                    limit=1,
                )
        return attachments

    def _write(self, vals):
        # If we are writing the state (computed) and we are a stock.picking
        # which uses DHL...
        if vals.get("state") == "assigned":
            invalid_ids = []
            for sp in self:
                carrier = sp.carrier_id
                if (
                    carrier
                    and carrier.allows_dhl_validation()
                    and carrier.delivery_type == "dhl_de"
                    and not self.env.context.get("sale_amazon_get_order")
                ):
                    (is_address_valid, validation_dhl,) = sp.carrier_id.dhl_validation(
                        sp, None
                    )
                    if not is_address_valid:
                        invalid_ids.append(sp.id)
                        new_vals = vals.copy()
                        new_vals["state"] = "waiting"
                        new_vals.update(
                            {
                                "has_errors_address_dhl": True,
                                "feedback_validation_address_dhl": validation_dhl,
                            }
                        )
                        super(StockPicking, sp)._write(new_vals)
            new_self = self.filtered(lambda s: s.id not in invalid_ids)
            if not new_self:
                return True
            vals = vals.copy()
            vals.update(
                {
                    "has_errors_address_dhl": False,
                    "feedback_validation_address_dhl": None,
                }
            )
            return super(StockPicking, new_self)._write(vals)
        return super(StockPicking, self)._write(vals)

    def action_assign(self):
        for sp in self.filtered("has_errors_address_dhl"):
            sp._compute_state()
        return super(StockPicking, self).action_assign()

    def get_additional_dhl_label_manually(self):
        self.ensure_one()
        if self.carrier_id.delivery_type != "dhl_de":
            raise UserError(_("The provider of the carrier is not DHL DE"))
        self.send_to_shipper()
        return True
