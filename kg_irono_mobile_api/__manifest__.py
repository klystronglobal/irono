# -*- coding: utf-8 -*-
{
    "name": "KG IRONO Mobile API",
    "summary": """KG Mobile API""",
    "category": "Website",
    "version": "17.0.0",
    "author": "Klystron Global",
    "maintainer": "Aravind",
    "license": "Other proprietary",
    "website": "https://klystronglobal.com",
    "depends": ['web', 'base', 'product', 'sale'],
    "data": [
        'security/ir.model.access.csv',
        'data/banner_sequence.xml',
        'data/demo.xml',
        'views/banner.xml',
        'views/product.xml',
        'views/res_partner.xml',
        'views/saleorder.xml',
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
