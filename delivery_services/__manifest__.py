##############################################################################
#
#    Copyright (c) 2022 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
{
    "name": "Delivery Services Configuration",
    "summary": "Delivery Services Configuration",
    "version": "13.0.1.0.0",
    "author": "brain-tec AG, Odoo Community Association (OCA)",
    "maintainer": "brain-tec AG",
    "license": "AGPL-3",
    "category": "Delivery",
    "complexity": "normal",
    "depends": ["delivery", "stock", "base"],
    "website": "https://github.com/OCA/delivery-carrier",
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
        "views/picking_service.xml",
        "views/shipment_service.xml",
        "views/shipment_service_attribute.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": True,
}
