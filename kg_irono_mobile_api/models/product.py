# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProductInherit(models.Model):
    _inherit = "product.product"

    irono_service = fields.Boolean('Irono Service', default=False)
    kg_partner_id = fields.Many2one('res.partner', 'Vendor')
