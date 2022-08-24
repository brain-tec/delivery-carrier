##############################################################################
#
#    Copyright (c) 2022 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
{
    "name": "DHL Germany Shipping",
    "summary": "Print DHL DE shipping labels",
    "version": "15.0.1.0.0",
    "author": "brain-tec AG, Odoo Community Association (OCA)",
    "maintainer": "brain-tec AG",
    "license": "AGPL-3",
    "category": "Delivery",
    "complexity": "normal",
    "depends": ["delivery", "mail", "base", "base_address_extended"],
    "website": "https://github.com/OCA/delivery-carrier",
    "data": [
        "views/delivery_carrier.xml",
        "views/stock_picking_views.xml",
        "views/view_res_partner.xml",
        "views/sale_order_views.xml",
    ],
    "external_dependencies": {"python": ["zeep", "defusedxml"]},
    "installable": True,
    "auto_install": False,
    "application": True,
}
