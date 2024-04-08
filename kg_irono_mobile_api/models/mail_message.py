# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MailMessageInherit(models.Model):
    _inherit = "mail.message"

    irono_service = fields.Boolean('Irono Service', default=False)
    irono_type = fields.Selection([('vendor','Vendor'),('customer','Customer')],'Irono Service')
