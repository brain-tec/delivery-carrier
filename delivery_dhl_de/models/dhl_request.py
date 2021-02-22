##############################################################################
#
#    Copyright (c) 2021 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
import os

from defusedxml.lxml import fromstring
import time
from lxml import etree
from zeep import Client, Plugin
from requests.auth import HTTPBasicAuth
from requests import Session
from zeep.transports import Transport

class DHLProvider():

    def __init__(self, debug_logger, http_user, http_password, request_type='createShipmentOrder',
                 prod_environment=False):
        self.debug_logger = debug_logger
        wsdl_url = 'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/3.1/geschaeftskundenversand-api-3.1.wsdl'
        if not prod_environment:
            self.url = 'https://cig.dhl.de/services/production/soap'
        else:
            self.url = 'https://cig.dhl.de/services/sandbox/soap'

        if request_type == "createShipmentOrder":
            self.client = self._set_client(wsdl_url, http_user, http_password)
            self.cis_factory = self.client.type_factory('ns0')
            self.bcs_factory = self.client.type_factory('ns1')
        elif request_type =="validateShipment":
            self.client = self._set_client(wsdl_url, http_user, http_password)
            self.cis_factory = self.client.type_factory('ns0')
            self.bcs_factory = self.client.type_factory('ns1')


    def _set_client(self, wsdl, http_user, http_password):
        url = 'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/3.1/geschaeftskundenversand-api-3.1.wsdl'
        url = 'https://cig.dhl.de/cig-wsdls/com/dpdhl/wsdl/geschaeftskundenversand-api/3.0/geschaeftskundenversand-api-3.0.wsdl'
        session = Session()
        session.auth = HTTPBasicAuth(http_user, http_password)
        transport = Transport(session=session)
        # transport.binding_classes = binding_classes
        wsdl = '../dhl_de_api/geschaeftskundenversand-api-3.1.wsdl'
        wsdl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), wsdl)
        client = Client('file:///%s' % wsdl_path.lstrip('/'), transport=transport)
        #client = Client(url, transport=transport)
        #client.set_ns_prefix('soapenv', "http://schemas.xmlsoap.org/soap/envelope/")

        return client

    def _set_CreateShipmentOrderRequest(self):
        element = self.client.get_element('ns1:CreateShipmentOrderRequest')

    def _set_version(self):
        result = self.client.get_element('ns1:Version')(3, 1)
        return result

    def _set_authentication(self, site_id, password):
        self.user = site_id
        self.signature = password
        authentication = self.cis_factory.AuthentificationType()
        authentication['user'] = site_id
        authentication['signature'] = password
        authentication = {'Authentification' : authentication}
        #self.client.set_default_soapheaders(authentication)

    def _set_ShipmentOrder(self, picking, dhl_product, ekp_number, weight):
        shipmentOrder  =  self.bcs_factory.ShipmentOrderType()
        ShipmentDetails = self.bcs_factory.ShipmentDetailsTypeType()
        picking_company_id = picking.picking_type_id and picking.picking_type_id.warehouse_id and \
                             picking.picking_type_id.warehouse_id.partner_id
        Shipment = {'ShipmentDetails':ShipmentDetails}
        shipmentOrder.sequenceNumber = "01"
        shipmentOrder.Shipment = Shipment
        ShipmentDetails.product = dhl_product
        ShipmentDetails.accountNumber = ekp_number
        ShipmentDetails.shipmentDate = time.strftime("%Y-%m-%d")
        ShipmentDetails.ShipmentItem = self._set_shipmentItem(weight)
        ShipmentDetails.Notification = self._set_Notificaiton(picking_company_id)
        Shipment.update({'Shipper': self._set_shipper(picking_company_id, picking.carrier_id),
                         'Receiver' : self._set_receiver(picking.partner_id, picking.carrier_id)
                         })
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
        receiver.Communication = communication
        return receiver

    def _set_LabelResponseType(self, label_format):
        label = None
        if label_format == 'PDF':
            label = self.client.get_element('ns1:labelResponseType')('B64')
        else:
            label = self.client.get_element('ns1:labelResponseType')('ZPL2')
        return label

        return receiver

    def _process_shipment(self, shipment_request):
        ShipmentRequest  = self.client.get_element('ns1:CreateShipmentOrderRequest')
        document = etree.Element('root')
        ShipmentRequest.render(document, shipment_request)
        soapheader = self.client.get_element("ns0:Authentification")(self.user, self.signature)
        document = self.client.create_message(self.client.service, self.client.service.createShipmentOrder._op_name
                                              , _soapheaders=[soapheader], **shipment_request)
        #self.client.service.createShipmentOrder(**shipment_request, _soapheaders=[soapheader])
        request_to_send = etree.tostring(document, xml_declaration=False, encoding='utf-8')
        headers = {'Content-Type': 'text/xml'}
        response = self.client.transport.post(self.url, request_to_send, headers=headers)
        if self.debug_logger:
            self.debug_logger(request_to_send, 'dhl_shipment_request')
            self.debug_logger(response.content, 'dhl_shipment_response')
        if response.status_code != 200 :
            raise Warning(response.content)
        response_element_xml = fromstring(response.content.decode(response.encoding))
        response_element = response_element_xml.find("*//bcs:CreateShipmentOrderResponse", response_element_xml.nsmap)
        Response = self.client.get_element("ns1:CreateShipmentOrderResponse")
        response_zeep = Response.type.parse_xmlelement(response_element)
        return response_zeep
