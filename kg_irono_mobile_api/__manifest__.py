# -*- coding: utf-8 -*-
{
    "name": "KG IRONO Mobile API",
    "summary": """KG Mobile API""",
    "category": "Extra Tools",
    "version": "17.1.1",
    "sequence": 1,
    "author": "Klystron Global",
    "maintainer": "Aravind",
    "license": "AGPL-3",
    "website": "https://klystronglobal.com",
    "depends": ['web', 'base', 'product', 'sale', 'helpdesk_mgmt'],
    "data": [
        'security/ir.model.access.csv',
        'data/banner_sequence.xml',
        'views/banner.xml',
        'views/product.xml',
        'views/res_partner.xml',
        'views/saleorder.xml',
        'views/res_config.xml',
        'views/twilio_account.xml',
        'views/menus.xml',
    ],
    'external_dependencies': {
        'python': ['twilio']
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}
