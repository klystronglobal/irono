# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductProductInherit(models.Model):
    _inherit = "product.product"

    irono_service = fields.Boolean('Irono Service', default=False)
    kg_partner_id = fields.Many2one('res.partner', 'Vendor')

class ProductCategoryInherit(models.Model):
    _inherit = "product.category"

    image_1920 = fields.Image('Image')
    irono_service = fields.Boolean('Publish In App', default=False)
