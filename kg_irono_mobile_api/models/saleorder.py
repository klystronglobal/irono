# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderInherit(models.Model):
    _inherit = "sale.order"

    irono_service = fields.Boolean('Irono Service', default=False)
    kg_vendor_id = fields.Many2one('res.partner', 'Vendor')
