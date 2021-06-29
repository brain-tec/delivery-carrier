##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
import os
import time

from lxml import etree

from defusedxml.lxml import fromstring
from requests import Session
from requests.auth import HTTPBasicAuth
from zeep import Client
from zeep.transports import Transport


class DHLProvider:
    def __init__(self, debug_logger, http_user, http_password, prod_environment=False):
        self.debug_logger = debug_logger
        if prod_environment:
            self.url = "https://cig.dhl.de/services/production/soap"
        else:
            self.url = "https://cig.dhl.de/services/sandbox/soap"
        self.client = self._set_client(http_user, http_password)
        self.cis_factory = self.client.type_factory("ns0")
        self.bcs_factory = self.client.type_factory("ns1")

    def _set_client(self, http_user, http_password):
        session = Session()
        session.auth = HTTPBasicAuth(http_user, http_password)
        transport = Transport(session=session)
        wsdl = "../dhl_de_api/geschaeftskundenversand-api-3.1.wsdl"
        wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), wsdl)
        client = Client("file:///%s" % wsdl_path.lstrip("/"), transport=transport)
        return client

    def _set_version(self):
        result = self.client.get_element("ns1:Version")(3, 1)
        return result

    def _set_authentication(self, site_id, password):
        self.user = site_id
        self.signature = password

    def _set_ShipmentOrder(self, picking, order, dhl_product, ekp_number, weight):
        shipmentOrder = self.bcs_factory.ShipmentOrderType()
        ShipmentDetails = self.bcs_factory.ShipmentDetailsTypeType()
        if picking:
            shipper_partner_id = picking.picking_type_id.warehouse_id.partner_id
            receiver_partner_id = picking.partner_id
            shipment_carrier_id = picking.carrier_id
        elif order:
            shipper_partner_id = order.warehouse_id.partner_id
            receiver_partner_id = order.partner_shipping_id
            shipment_carrier_id = order.carrier_id
        Shipment = {"ShipmentDetails": ShipmentDetails}
        shipmentOrder.sequenceNumber = "01"
        shipmentOrder.Shipment = Shipment
        ShipmentDetails.product = dhl_product
        ShipmentDetails.accountNumber = ekp_number
        ShipmentDetails.shipmentDate = time.strftime("%Y-%m-%d")
        ShipmentDetails.ShipmentItem = self._set_shipmentItem(weight)
        ShipmentDetails.Notification = self._set_Notificaiton(shipper_partner_id)
        Shipment.update(
            {
                "Shipper": self._set_shipper(shipper_partner_id, shipment_carrier_id),
                "Receiver": self._set_receiver(
                    receiver_partner_id, shipment_carrier_id
                ),
            }
        )
        return shipmentOrder

    def _set_shipmentItem(self, weight):
        ShipmentItem = self.bcs_factory.ShipmentItemType()
        ShipmentItem.weightInKG = weight
        return ShipmentItem

    def _set_Notificaiton(self, partner):
        notification = self.bcs_factory.ShipmentNotificationType()
        notification.recipientEmailAddress = partner.email
        return notification

    def _set_shipper(self, partner, carrier):
        shipper = self.bcs_factory.ShipperType()
        address = self.cis_factory.NativeAddressType()
        communication = self.cis_factory.CommunicationType()
        country = self.cis_factory.CountryType()
        shipper.Name = self._set_name(partner)
        shipper.Address = address
        street, street_no = carrier.get_street_and_number_from_partner(partner)
        if not street:
            street = partner.street
            street_no = partner.street_no if partner.street_no else ""
        address.streetName = street
        address.streetNumber = street_no
        address.zip = partner.zip
        address.city = partner.city
        address.Origin = country
        country.countryISOCode = partner.country_id and partner.country_id.code or ""
        shipper.Communication = communication
        if partner.phone:
            communication.phone = partner.phone
        return shipper

    def _set_name(self, partner):
        name = self.cis_factory.NameType()
        name.name1 = partner.name
        return name

    def _set_receiver(self, partner, carrier):
        receiver = self.bcs_factory.ReceiverType()
        address = self.cis_factory.ReceiverNativeAddressType()
        country = self.cis_factory.CountryType()
        communication = self.cis_factory.CommunicationType()
        packstation = {}
        receiver.name1 = partner.name
        receiver.Address = address
        street, street_no = carrier.get_street_and_number_from_partner(partner)
        if not street:
            street = partner.street
            street_no = partner.street_no if partner.street_no else ""
        address.streetName = street
        address.streetNumber = street_no
        address.zip = partner.zip
        address.city = partner.city
        address.Origin = country
        country.countryISOCode = partner.country_id and partner.country_id.code or ""
        street_name = partner.street_name or ""
        if any('packstation' in s for s in [street_no.lower(), street_name.lower()]):
            address.streetName = 'Packstation'
            if len(street.split(' ')) > 1:
                packstation['packstationNumber'] = street.split(' ')[0]
                packstation['postNumber'] = street.split(' ')[1]
                address.streetNumber = street.split(' ')[0]
                address.name2 = street.split(' ')[1]
            else:
                packstation['packstationNumber'] = street_no
                packstation['postNumber'] = partner.street2 or ""
                address.streetNumber = street_no
                address.name2 = partner.street2
            receiver.Packstation = packstation
        if partner.email:
            communication.email = partner.email
        receiver.Communication = communication
        return receiver

    def _process_shipment(self, shipment_request, request_type):
        if request_type == "createShipmentOrder":
            service_name = self.client.service.createShipmentOrder._op_name
            response_element_name = "ns1:CreateShipmentOrderResponse"
            find_response_element_name = "*//bcs:CreateShipmentOrderResponse"
        elif request_type == "validateShipment":
            service_name = self.client.service.validateShipment._op_name
            response_element_name = "ns1:ValidateShipmentResponse"
            find_response_element_name = "*//bcs:ValidateShipmentResponse"
        soapheader = self.client.get_element("ns0:Authentification")(
            self.user, self.signature
        )
        document = self.client.create_message(
            self.client.service,
            service_name,
            _soapheaders=[soapheader],
            **shipment_request
        )
        request_to_send = etree.tostring(
            document, xml_declaration=False, encoding="utf-8"
        )
        headers = {
            "Content-Type": "application/soap+xml;charset=UTF-8",
            "SOAPAction": "urn:%s" % request_type,
            "Content-Length": str(len(request_to_send)),
        }
        response = self.client.transport.post(
            self.url, request_to_send, headers=headers
        )
        if self.debug_logger:
            self.debug_logger(request_to_send, "dhl_shipment_request")
            self.debug_logger(response.content, "dhl_shipment_response")
        if response.status_code != 200:
            raise Warning(response.content)
        response_element_xml = fromstring(response.content.decode(response.encoding))
        shipment_response_element = response_element_xml.find(
            find_response_element_name, response_element_xml.nsmap
        )
        Response = self.client.get_element(response_element_name)
        response_zeep = Response.type.parse_xmlelement(shipment_response_element)
        return response_zeep
