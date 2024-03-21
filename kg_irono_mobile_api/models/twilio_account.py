# -*- coding: utf-8 -*-
from odoo import fields, models, _
from twilio.rest import Client
from twilio.base.exceptions import TwilioException


class TwilioAccount(models.Model):
    """Create Twilio account to set the details of Twilio account,
    can set the number and auth token"""
    _name = 'twilio.account'
    _description = 'Twilio Account'

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Name', required=True, help='Name for Twilio '
                                                          'account')
    account_sid = fields.Char(string='Account SID', required=True,
                              help='Account SID for connecting with Twilio')
    auth_token = fields.Char(string='Auth Token', required=True,
                             help='Auth Token for connecting with Twilio')
    from_number = fields.Char(string='Your Twilio Phone Number', required=True,
                              help='Twilio account number')
    to_number = fields.Char(string='To', required=True,
                            help='Recipient number with country code for '
                                 'testing the connection(It should be '
                                 'added to Verified Caller IDs in Twilio).')
    body = fields.Text(string='Body', required=True,
                       help='Body for test message',
                       default='This Message is for testing Twilio Connection')
    state = fields.Selection([
        ('new', 'New'),
        ('confirm', 'Connected'),
    ], required=True, default='new', string='State', help='State of Twilio '
                                                          'account')

    def action_test_connection(self):
        """Send test sms for checking the connection"""
        try:
            message = Client(self.account_sid, self.auth_token).messages.create(
                body=self.body,
                from_=self.from_number,
                to=self.to_number
            )
            if message.sid:
                self.write({'state': 'confirm'})
                message_data = _("Connection Successful!")
                message_type = 'success'
            else:
                message_data = _("Connection Not Successful!")
                message_type = 'warning'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message_data,
                    'type': message_type,
                    'sticky': True,
                }
            }
        except TwilioException:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("Connection Not Successful!"),
                    'type': 'warning',
                    'sticky': True,
                }
            }
