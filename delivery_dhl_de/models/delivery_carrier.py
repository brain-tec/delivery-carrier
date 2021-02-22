##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.delivery_dhl_de.dhl_api.dhl_response import Response
from odoo.addons.delivery_dhl_de.models.dhl_request import DHLProvider
import xml.etree.ElementTree as etree
import requests
from requests.auth import HTTPBasicAuth
import binascii
from re import findall


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
    dhl_de_package_weight_unit = fields.Selection([('L', 'Pounds'),
                                                ('K', 'Kilograms')],
                                               default='K',
                                               string="Package Weight Unit")
    dhl_de_default_packaging_id = fields.Many2one('product.packaging', string='DHL Default Packaging Type')
    dhl_de_label_format = fields.Selection([('PDF', 'PDF'),
        ('ZPL2', 'ZPL2'),
    ], string="Label Image Format", default='PDF')
    export_type = fields.Selection([("OTHER", "OTHER"),
                                    ("PRESENT", "PRESENT"),
                                    ("COMMERCIAL_SAMPLE", "COMMERCIAL_SAMPLE"),
                                    ("DOCUMENT", "DOCUMENT"),
                                    ("RETURN_OF_GOODS", "RETURN_OF_GOODS")], string="Export Type",
                                   help="Depends on chosen product only mandatory for international and non EU shipments.")

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
        response = []
        context = self._context
        for picking in pickings:
            shipment_request = {}
            srm = DHLProvider(self.log_xml, http_user=self.dhl_de_http_userid,
                              http_password=self.dhl_de_http_password, request_type="createShipmentOrder",
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

            if self.dhl_de_label_format == 'PDF':
                shipment_request['labelResponseType'] = 'B64'
            else:
                shipment_request['labelResponseType'] = 'ZPL2'
            dhl_response = srm._process_shipment(shipment_request)
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
            shipping_data = {
                'exact_price': picking.sale_id and picking.sale_id.delivery_price or 0.0,
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

    def dhl_validation(self, shipper, receiver):
        self.ensure_one()
        root_node = etree.Element("soapenv:Envelope")
        root_node.attrib['xmlns:soapenv'] = "http://schemas.xmlsoap.org/soap/envelope/"
        root_node.attrib['xmlns:cis'] = "http://dhl.de/webservice/cisbase"
        root_node.attrib['xmlns:ns'] = "http://dhl.de/webservices/businesscustomershipping/3.0"

        header_node = etree.SubElement(root_node, "soapenv:Header")
        authentification_node = etree.SubElement(header_node, "cis:Authentification")
        etree.SubElement(authentification_node, "cis:user").text = str(
            self.dhl_de_user_id
        )
        etree.SubElement(authentification_node, "cis:signature").text = str(
            self.dhl_de_password
        )

        shipment_body_node = etree.SubElement(root_node, "soapenv:Body")
        validateshipment_order_node = etree.SubElement(shipment_body_node, "ns:ValidateShipmentOrderRequest")
        version_node = etree.SubElement(validateshipment_order_node, "ns:Version")
        etree.SubElement(version_node, "majorRelease").text = "3"
        etree.SubElement(version_node, "minorRelease").text = "0"

        shipment_order_node = etree.SubElement(validateshipment_order_node, "ShipmentOrder")
        etree.SubElement(shipment_order_node, "sequenceNumber").text = "01"
        shipment_node = etree.SubElement(shipment_order_node, "Shipment")
        shipment_details_node = etree.SubElement(shipment_node, "ShipmentDetails")
        etree.SubElement(shipment_details_node, "product").text = str(self.dhl_de_services_name)

        account_number = self.dhl_de_ekp_no + self.dhl_de_services_name[1:3] + "01"

        etree.SubElement(shipment_details_node, "cis:accountNumber").text = str(account_number)

        etree.SubElement(shipment_details_node, "shipmentDate").text = fields.Date.to_string(fields.Date.today())
        shipment_item = etree.SubElement(shipment_details_node, "ShipmentItem")
        etree.SubElement(shipment_item, "weightInKG").text = "5"  # 5 is hardcoded because is meaningless now

        shipper_node = etree.SubElement(shipment_node, "Shipper")
        shipper_name = etree.SubElement(shipper_node, "Name")
        etree.SubElement(shipper_name, "cis:name1").text = str(shipper.name)

        street, street_no = self.get_street_and_number_from_partner(shipper)
        if not street:
            street = str(shipper.street)
            street_no = "37"
        address_detail = etree.SubElement(shipper_node, "Address")
        etree.SubElement(address_detail, "cis:streetName").text = street
        etree.SubElement(address_detail, "cis:streetNumber").text = street_no
        etree.SubElement(address_detail, "cis:addressAddition").text = str(
            shipper.street2 if shipper.street2 else ""
        )
        etree.SubElement(address_detail, "cis:zip").text = str(shipper.zip)
        etree.SubElement(address_detail, "cis:city").text = str(shipper.city)
        origin_node = etree.SubElement(address_detail, "cis:Origin")
        etree.SubElement(origin_node, "cis:country").text = str(
            shipper.country_id and shipper.country_id.display_name or ""
        )
        etree.SubElement(origin_node, "cis:countryISOCode").text = str(
            shipper.country_id and shipper.country_id.code or ""
        )
        communication_node = etree.SubElement(shipper_node, "Communication")
        if shipper.phone:
            etree.SubElement(communication_node, "cis:phone").text = str(shipper.phone)

        receiver_node = etree.SubElement(shipment_node, "Receiver")
        etree.SubElement(receiver_node, "cis:name1").text = str(receiver.name)
        address_node = etree.SubElement(receiver_node, "Address")

        street, street_no = self.get_street_and_number_from_partner(receiver)
        if not street:
            street = str(receiver.street)
            street_no = "37"
        etree.SubElement(address_node, "cis:streetName").text = street
        etree.SubElement(address_node, "cis:streetNumber").text = street_no
        etree.SubElement(address_node, "cis:zip").text = str(receiver.zip)
        etree.SubElement(address_node, "cis:city").text = str(receiver.city)
        origin = etree.SubElement(address_node, "cis:Origin")
        etree.SubElement(origin, "cis:country").text = str(
            receiver.country_id and receiver.country_id.display_name or ""
        )
        etree.SubElement(origin, "cis:countryISOCode").text = str(
            receiver.country_id and receiver.country_id.code
        )

        if receiver.phone or receiver.email:
            communication_node = etree.SubElement(receiver_node, "Communication")
            if receiver.phone:
                etree.SubElement(communication_node, "cis:phone").text = str(receiver.phone)
            if receiver.email:
                etree.SubElement(communication_node, "cis:email").text = str(receiver.email)

        headers = {
            "Content-Type": "application/soap+xml;charset=UTF-8",
            "SOAPAction": "urn:createShipmentOrder",
            'Content-Length': str(len(etree.tostring(root_node))),
        }
        url = self.dhl_de_endpoint_url
        _logger.debug("DHL ValidateShipmentOrderRequest.\n"
                      " - DHL Request URL : %s\n"
                      " - DHL Request Header: %s\n"
                      " - DHL Request Data : %s" % (url, headers, etree.tostring(root_node)))
        result = requests.post(url=url, data=etree.tostring(root_node), headers=headers,
                               auth=HTTPBasicAuth(str(self.dhl_de_http_userid),
                                                  str(self.dhl_de_http_password)))
        if result.status_code != 200:
            error = _("Error Code : %s - %s") % (result.status_code, result.reason)
            raise UserError(error)

        api = Response(result)
        result = api.dict()
        return self.check_error_in_response_validation(result)

    @api.model
    def check_error_in_response_validation(self, response):
        """ Generate the dynamic error in DHL response when we have an error response.
            Based on the method check_error_in_response()
            @param Response Detail
            @return: Dynamic Error when error want to generate.
        """
        msg = _("Error Code : %s - %s")
        fault_res = response.get('Envelope', {}).get('Body', {}).get('Fault', {})
        if fault_res:
            response_code = fault_res.get('faultcode')
            status_text = fault_res.get('faultstring')
            error = msg % (response_code, status_text)
            if response_code != "0":
                return False, error
        else:
            response_detail = response.get('Envelope', {}).get('Body', {}).get('ValidateShipmentResponse', {})
            response_code = response_detail.get('Status', {}).get('statusCode')
            status_text = response_detail.get('Status', {}).get('statusText')

            if isinstance(response_detail, dict):
                response_detail = [response_detail]
            for detail in response_detail:
                validation_detail = detail.get('ValidationState', {})
                if validation_detail:
                    if isinstance(validation_detail, dict):
                        validation_detail = [validation_detail]
                    for vdetail in validation_detail:
                        custom_status_text = vdetail.get('Status', {}).get('statusText')
                        custom_status_msg = vdetail.get('Status', {}).get('statusMessage')
                        if custom_status_msg:
                            if not isinstance(custom_status_msg, list):
                                custom_status_msg = [custom_status_msg]
                            if not custom_status_text:
                                custom_status_text = '\n'.join(custom_status_msg)
                            else:
                                custom_status_text += '\n' + '\n'.join(custom_status_msg)
                        status_code = vdetail.get('Status', {}).get('statusCode')
                        error = msg % (status_code, custom_status_text)
                        if status_code != "0":
                            return False, error
            error = msg % (response_code, status_text)
            if response_code != "0":
                return False, error
        return True, ''

