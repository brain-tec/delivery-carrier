.. image:: https://img.shields.io/badge/license-LGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

===========================
Stock Picking Delivery Rate
===========================

This module adds the concept of delivery rate quotes & purchasing
on Stock Pickings

This is meant to be combined with an external connector with a carrier
supplier in order to bring in rate quotes, although they can be created &
edited manually if your workflow calls for it.

Usage
=====

Dispatch rates can be added in Stock Picking

Purchase Rate
-------------

The Purchase Rate wizard can be accessed by clicking the green check next
to the rate quote in a ``stock.picking``.

Completing this wizard will create ``purchase.order`` for your rate.
If using a connector, this is the point in which a shipment purchase would
be triggered.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/99/9.0

Known issues / Roadmap
======================

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/delivery-carrier/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Dave Lasley <dave@laslabs.com>
* Brett Wood <bwood@laslabs.com>
* Ted Salmon <tsalmon@laslabs.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
