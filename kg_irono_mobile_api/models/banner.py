# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Banner(models.Model):
    _name = "irono.banner"
    _description = "Offer Banners"

    name = fields.Char('Name')
    active = fields.Boolean('Active',default=True)
    background_image = fields.Image('Background Image')
    background_color = fields.Char('Background Color')
    sub_heading = fields.Char('Sub Heading')
    main_heading = fields.Char('Main Heading')
    button_text = fields.Char('Button Text')
    offers_for = fields.Selection([('vendor','Vendors'),('customer','Customers')])
    product_id = fields.Many2one('product.product', 'Service', domain="[('irono_service', '=', True)]")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('irono.offer.banner') or '/'
        return super().create(vals_list)
