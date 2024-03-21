# -*- coding: utf-8 -*-
from odoo import api, fields, models


class InitialOtp(models.Model):
    _name = 'irono.initial.otp'

    initial_user_login = fields.Text('User Logs', default="{}")
