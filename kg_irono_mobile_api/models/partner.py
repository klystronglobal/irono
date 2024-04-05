# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartnerInherit(models.Model):
    _inherit = "res.partner"

    kg_partner_type = fields.Selection([('vendor', 'Vendor'), ('customer', 'Customer')], 'Type', tracking=True)
    product_ids = fields.One2many('product.product', 'kg_partner_id', 'Services')
    saleorder_ids = fields.One2many('sale.order', 'kg_vendor_id', 'Vendor')
    favourite_product_ids = fields.Many2many('product.product', string='Services',
                                             domain="[('irono_service', '=', True)]")
    kg_otp = fields.Integer('OTP')
    description = fields.Text('About', tracking=True)
    bussiness_name = fields.Char('Bussiness Name', tracking=True)
    bussiness_phone = fields.Char('Bussiness Phone', tracking=True)
    bussiness_email = fields.Char('Bussiness Email', tracking=True)
    bussiness_image = fields.Binary('Shop Image')
    bussiness_document = fields.Binary('Gov Documents')
    verified_vendor = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('verified', 'Verified')],
                                       'Verification Status', tracking=True,default="draft")

    def confirm_vendor_verification(self):
        for rec in self:
            rec.write({'verified_vendor': 'verified'})

    def revoke_vendor_verification(self):
        for rec in self:
            rec.write({'verified_vendor': 'draft'})
