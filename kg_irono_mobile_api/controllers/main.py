# -*- coding: utf-8 -*-
from odoo import http
import json
from odoo.http import request
from twilio.rest import Client
import random
import logging
import ast
from odoo.addons.kg_irono_mobile_api.common import (valid_response, invalid_response, ROUTE_BASE, get_user)

_logger = logging.getLogger(__name__)
from twilio.base.exceptions import TwilioException


class Irono(http.Controller):

    @http.route('/user/login', methods=["POST"], type="json", auth="none", csrf=False)
    def user_login_phone(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        partner_id = self.check_user_exist(phone)
        if partner_id:
            _logger.info("Already a user")
            login_otp = self.generate_login_otp()
            partner_id.sudo().write({'kg_otp': login_otp})
            self.send_login_otp(login_otp, phone)
        else:
            _logger.info("New user.")
            initial_partner = request.env['irono.initial.otp'].sudo().search([], limit=1)
            if initial_partner and initial_partner.initial_user_login:
                values = ast.literal_eval(initial_partner.initial_user_login)
                login_otp = self.generate_login_otp()
                values[phone] = login_otp
                initial_partner.write({'initial_user_login': values})
                self.send_login_otp(login_otp, phone)
        return True

    @http.route('/user/submit/otp', methods=["POST"], type="json", auth="public", csrf=False)
    def user_login_otp(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        otp = data.get('otp', False)
        result = self.check_user_otp(phone, int(otp))
        if result:
            values = self.home_page_values(result)
            return valid_response(values, message='User Authentication Successfull !',
                                  is_http=False)
        else:
            return valid_response({}, message='User Authentication Failed !',
                                  is_http=False)

    def home_page_values(self, partner_id):
        if partner_id:
            values = {}
            values['user_name'] = partner_id.name if partner_id.name else ''
            values['user_type'] = partner_id.kg_partner_type if partner_id.kg_partner_type else ''
            if partner_id.kg_partner_type == 'customer':
                banners = request.env['irono.banner'].sudo().search_read(
                    [('offers_for', '=', 'customer'), ('active', '=', True)],
                    ['name', 'background_color', 'sub_heading', 'main_heading', 'button_text', 'product_id'])
                service_providers = request.env['res.partner'].sudo().search_read(
                    [('kg_partner_type', '=', 'vendor')], ['name'])
                service_category = request.env['product.category'].sudo().search_read([], ['name'])
                values['service_providers'] = service_providers
                values['service_categories'] = service_category
                values['banners'] = banners
            elif partner_id.kg_partner_type == 'vendor':
                banners = request.env['irono.banner'].sudo().search_read(
                    [('offers_for', '=', 'customer'), ('active', '=', True)],
                    ['name', 'background_color', 'sub_heading', 'main_heading', 'button_text', 'product_id'])
                values['banners'] = banners
            else:
                pass
            return values

    def check_user_exist(self, phone):
        if phone:
            partner = request.env['res.partner'].sudo().search([('phone', '=', phone)])
            return partner
        else:
            return False

    def send_login_otp(self, otp, phone):
        account_id = request.env['twilio.account'].sudo().search([('active', '=', True)], limit=1)
        if account_id:
            try:
                client = Client(account_id.account_sid,
                                account_id.auth_token)
                message = client.messages.create(
                    body=str(otp) + " is your IRONO OTP. Do not share it with anyone.",
                    from_=account_id.from_number,
                    to=phone
                )
                if message.sid:
                    _logger.info("OTP send to user.")
                else:
                    _logger.info("OTP not send to user.")
            except TwilioException:
                _logger.info("OTP not send to user.")

    def generate_login_otp(self):
        return random.randint(1000, 9999)

    def check_user_otp(self, phone, otp):
        partner_id = self.check_user_exist(phone)
        if partner_id and partner_id.kg_otp:
            if partner_id.kg_otp == otp:
                return partner_id
            return False
        else:
            initial_partner = request.env['irono.initial.otp'].sudo().search([], limit=1)
            if initial_partner and initial_partner.initial_user_login:
                values = ast.literal_eval(initial_partner.initial_user_login)
                if values.get(str(phone)) and values.get(str(phone)) == otp:
                    # Hardcoding as Customer for testing purpose...
                    partner = request.env['res.partner'].sudo().create(
                        {'phone': phone, 'name': ' ', 'kg_partner_type': 'customer'})
                    _logger.info("Partner created. ID = " + str(partner.id))
                    return partner
            return False
