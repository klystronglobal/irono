# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigInherit(models.TransientModel):
    _inherit = "res.config.settings"

    terms_and_conditions_irono = fields.Char('Terms & Conditions', config_parameter="kg_irono_mobile_api.terms_and_conditions_irono")
    privacy_and_policy_irono = fields.Char('Privacy & Policy', config_parameter="kg_irono_mobile_api.privacy_and_policy_irono")
