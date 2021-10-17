import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-delivery-carrier",
    description="Meta package for oca-delivery-carrier Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-base_delivery_carrier_label',
        'odoo11-addon-delivery_auto_refresh',
        'odoo11-addon-delivery_carrier_label_default',
        'odoo11-addon-delivery_carrier_label_postlogistics',
        'odoo11-addon-delivery_carrier_partner',
        'odoo11-addon-delivery_free_fee_removal',
        'odoo11-addon-delivery_multi_destination',
        'odoo11-addon-delivery_price_rule_untaxed',
        'odoo11-addon-partner_delivery_schedule',
        'odoo11-addon-partner_delivery_zone',
        'odoo11-addon-stock_picking_report_delivery_cost',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 11.0',
    ]
)
