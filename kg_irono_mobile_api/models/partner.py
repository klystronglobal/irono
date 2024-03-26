# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    kg_partner_type = fields.Selection([('vendor', 'Vendor'), ('customer', 'Customer')], 'Type')
    product_ids = fields.One2many('product.product', 'kg_partner_id', 'Services')
    saleorder_ids = fields.One2many('sale.order', 'kg_vendor_id', 'Vendor')
    favourite_product_ids = fields.Many2many('product.product', string='Services',
                                             domain="[('irono_service', '=', True)]")
    kg_otp = fields.Integer('OTP')
    description = fields.Text('About')
