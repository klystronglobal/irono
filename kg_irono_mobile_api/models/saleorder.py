# -*- coding: utf-8 -*-
from odoo import api, fields, models
import random


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    irono_service = fields.Boolean('Irono Service', default=False)
    kg_vendor_id = fields.Many2one('res.partner', 'Vendor')
    vendor_otp = fields.Char('Vendor OTP', help="OTP for vendor to completed the order.")

    def action_confirm(self):
        res = super(SaleOrderInherit, self).action_confirm()
        self.write({'vendor_otp': random.randint(1000, 9999)})
        return res
