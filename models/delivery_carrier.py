##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.delivery_dhl_de.models.dhl_request import DHLProvider
import binascii
from re import findall

import logging
_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    """ Add service group """

    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[("dhl_de", "DHL DE")])

    dhl_de_user_id = fields.Char("DHL UserId", copy=False, help="When use the sandbox account developer id use as "
                                                                "the userId.When use the live account application "
                                                                "id use as the userId.")
    dhl_de_password = fields.Char("DHL Password", copy=False, help="When use the sandbox account developer portal "
                                                                   "password use to as the password.When use the "
                                                                   "live account application token use to as the "
                                                                   "password.")
    dhl_de_http_userid = fields.Char("HTTP UserId", copy=False, help="HTTP Basic Authentication.")
    dhl_de_http_password = fields.Char("HTTP Password", copy=False, help="HTTP Basic Authentication.")

    dhl_de_ekp_no = fields.Char("EKP Number", copy=False, help="The EKP number sent to you by DHL and it must be "
                                                               "maximum 10 digit allow.")
    dhl_de_services_name = fields.Selection([("V01PAK", "V01PAK-DHL PAKET"),
                                      ("V53WPAK", "V53WPAK-DHL PAKET International"),
                                      ("V54EPAK", "V54EPAK-DHL Europaket"),
                                      ],
                                     string="Product Name",
                                     help="Shipping Services those are accepted by DHL.")
    dhl_de_package_weight_unit = fields.Selection([('L', 'Pounds'), ('K', 'Kilograms')], default='K',
                                                  string="Package Weight Unit")
    dhl_de_default_packaging_id = fields.Many2one('product.packaging', string='DHL Default Packaging Type')
    dhl_de_label_format = fields.Selection([('PDF', 'PDF'), ('ZPL2', 'ZPL2'),], string="Label Image Format",
                                           default='PDF')
    export_type = fields.Selection([("OTHER", "OTHER"),
                                    ("PRESENT", "PRESENT"),
                                    ("COMMERCIAL_SAMPLE", "COMMERCIAL_SAMPLE"),
                                    ("DOCUMENT", "DOCUMENT"),
                                    ("RETURN_OF_GOODS", "RETURN_OF_GOODS")], string="Export Type",
                                   help="Depends on chosen product only mandatory for international and non EU "
                                        "shipments.")



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
        response = []
        for picking in pickings:
            shipment_request = {}
            srm = DHLProvider(self.log_xml, http_user=self.dhl_de_http_userid,
                              http_password=self.dhl_de_http_password,
                              prod_environment=self.prod_environment)
            site_id = self.sudo().dhl_de_user_id
            password = self.sudo().dhl_de_password
            shipment_request['Version'] = srm._set_version()
            srm._set_authentication(site_id, password)

            account_number = self.dhl_de_ekp_no + self.dhl_de_services_name[1:3] + "01"
            total_bulk_weight = self._dhl_de_convert_weight(picking.weight_bulk, self.dhl_de_package_weight_unit)
            if total_bulk_weight:
                shipment_request['ShipmentOrder'] = srm._set_ShipmentOrder(picking, self.dhl_de_services_name,
                                                                           account_number, total_bulk_weight)
            shipments = []
            for package in picking.package_ids:
                weight = self._dhl_de_convert_weight(package.shipping_weight, self.dhl_de_package_weight_unit)
                shipments.append(srm._set_ShipmentOrder(picking, self.dhl_de_services_name, account_number,
                                                        weight))
            if shipments:
                shipment_request['ShipmentOrder'] = shipments


            if self.dhl_de_label_format == 'PDF':
                shipment_request['labelResponseType'] = 'B64'
            else:
                shipment_request['labelResponseType'] = 'ZPL2'
            dhl_response = srm._process_shipment(shipment_request, "createShipmentOrder")
            for CreationState in dhl_response.CreationState:
                if CreationState.LabelData.Status.statusCode:
                    error_message = "DHL DE Error : %s"%(CreationState.LabelData.Status.statusMessage)
                    raise UserError(_(error_message))
            final_tracking_no = []
            for CreationState in dhl_response.CreationState:
                tracking_no = CreationState.LabelData.shipmentNumber or CreationState.shipmentNumber or \
                              "No Shipment Number"
                binary_data = CreationState.LabelData.labelData
                message = (_("Shipment created!<br/> <b>Shipment Tracking Number : </b>%s")
                               % tracking_no)
                output_format = self.dhl_de_label_format
                if output_format == 'PDF':
                    # In the case we have a pdf we have to encode the label data
                    binary_data = binascii.a2b_base64(str(binary_data))
                picking.message_post(body=message, attachments=[
                    ('DHL Label-%s.%s' % (tracking_no, output_format), binary_data)])
                if tracking_no:
                    final_tracking_no.append(tracking_no)
            delivery_price = 0.0
            if picking.sale_id:
                delivery_line = picking.sale_id.order_line.filtered(lambda l: l.is_delivery)
                if delivery_line:
                    delivery_price = delivery_line[0].price_subtotal
            shipping_data = {
                'exact_price': delivery_price,
                'tracking_number': ",".join(final_tracking_no)}
            response += [shipping_data]
        return response

    def _dhl_de_convert_weight(self, weight, unit):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if unit == 'L':
            weight = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'), round=False)
        else:
            weight = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)
        return weight

    def get_street_and_number_from_partner(self, partner):
        self.ensure_one()
        street_value = 'street_no'
        street_no = ''
        street = ''
        if street_value:
            if 'street_number' not in partner or not partner.street_number:
                street_no = getattr(partner, street_value, "")
                street_no = street_no if street_no else ""
                if street_no:
                    street_no = findall('\\d+', street_no)
                    if street_no:
                        street_no = street_no[0]
                if street_value == 'street':
                    street_no = getattr(partner, street_value, "")
                    street = str(street_no.replace(street_no if street_no else "" or "", ""))
                else:
                    street = partner.street
            else:
                street_no = '/'.join(filter(bool, [partner.street_number or "",
                                                   partner.street_number2 or ""]))
                street = (partner.street_name or '').strip()
        return street, street_no

    def allows_dhl_validation(self):
        """ A delivery carrier allows for DHL address validation if
            its delivery type is one of the kind of DHL.
        """
        self.ensure_one()
        return 'dhl_de' in (self.delivery_type or '').lower()

    def dhl_validation(self, picking):
        self.ensure_one()

        shipment_request = {}
        srm = DHLProvider(self.log_xml, http_user=self.dhl_de_http_userid, http_password=self.dhl_de_http_password,
                          prod_environment=self.prod_environment)
        site_id = self.sudo().dhl_de_user_id
        password = self.sudo().dhl_de_password
        shipment_request['Version'] = srm._set_version()
        srm._set_authentication(site_id, password)

        account_number = self.dhl_de_ekp_no + self.dhl_de_services_name[1:3] + "01"
        shipment_request['ShipmentOrder'] = srm._set_ShipmentOrder(picking, self.dhl_de_services_name,
                                                                       account_number, 5)

        dhl_response = srm._process_shipment(shipment_request, "validateShipment")
        msg = _("DHL DE Error Code : %s - %s")
        for ValidationState in dhl_response.ValidationState:
            if ValidationState.Status.statusCode:
                custom_status_msg = ValidationState.Status.statusMessage
                custom_status_text = ValidationState.Status.statusText
                if custom_status_msg:
                    if not isinstance(custom_status_msg, list):
                        custom_status_msg = [custom_status_msg]
                    if not custom_status_text:
                        custom_status_text = '\n'.join(custom_status_msg)
                    else:
                        custom_status_text += '\n' + '\n'.join(custom_status_msg)
                status_code = ValidationState.Status.statusCode
                error = msg % (status_code, custom_status_text)
                return False, error
            else:
                return True, ""
