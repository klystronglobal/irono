# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import http
import json, random, logging
from odoo.http import request
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from odoo.addons.kg_irono_mobile_api.common import (valid_response, invalid_response, ROUTE_BASE, get_user)

_logger = logging.getLogger(__name__)


class IronoVendor(http.Controller):

    @http.route('/vendor/login', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_login_phone(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        partner_id = self.check_user_exist(phone)
        if partner_id:
            _logger.info("Already a user")
            login_otp = self.generate_login_otp()
            partner_id.sudo().write({'kg_otp': login_otp})
            # self.send_login_otp(login_otp, phone)
            return valid_response({'result': True}, message='User Already Exists. Provide OTP !',
                                  is_http=False)
        else:
            return valid_response({'result': False}, message='User does not exists. Sign Up !',
                                  is_http=False)

    @http.route('/vendor/sign/up', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_sign_up(self, **post):
        data = json.loads(request.httprequest.data)
        values = {'kg_partner_type': 'vendor', 'active': False}
        phone = data.get('phone', False)
        if self.check_user_exist(phone):
            return valid_response({'result': False}, message='User Already Exists !',
                                  is_http=False)
        first_name = data.get('first_name', False)
        last_name = data.get('last_name', False)
        email = data.get('email', False)
        values['name'] = first_name + ' ' + (last_name if last_name else '')
        values['phone'] = phone
        values['email'] = email if email else ''
        partner_id = request.env['res.partner'].sudo().create(values)
        _logger.info("Created a partner...")
        login_otp = self.generate_login_otp()
        partner_id.sudo().write({'kg_otp': login_otp})
        # self.send_login_otp(login_otp, phone)
        return valid_response({'result': True}, message='Vendor details saved. Waiting for otp.',
                              is_http=False)

    @http.route('/vendor/submit/otp', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_login_otp(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        otp = data.get('otp', False)
        result = self.check_user_otp(phone, int(otp))
        if result:
            if not result.active:
                result.write({'active': True})
            if result.verified_vendor == 'draft':
                return valid_response({'result': 'draft', 'user': result.id},
                                      message='Please Submit Related Bussiness Documents !', is_http=False)
            if result.verified_vendor == 'pending':
                return valid_response({'result': 'pending', 'user': result.id},
                                      message='Verification Pending !', is_http=False)
            values = self.vendor_home_page_values(result)
            return valid_response(values, message='User Authentication Successfull !', is_http=False)
        else:
            return valid_response({'result': False}, message='User Authentication Failed !', is_http=False)

    @http.route('/vendor/submit/bussiness/details', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_submit_bussiness_details(self, **post):
        data = json.loads(request.httprequest.data)
        bussiness_name = data.get('name', False)
        bussiness_phone = data.get('phone', False)
        bussiness_email = data.get('email', False)
        user = data.get('user', False)
        partner_id = self.get_partner(user)
        if partner_id:
            partner_id.write({'bussiness_name': bussiness_name, 'bussiness_phone': bussiness_phone,
                              'bussiness_email': bussiness_email, 'verified_vendor': 'pending'})
            return valid_response({'result': True}, message='Bussiness Details Submitted Successfull !', is_http=False)

    @http.route('/vendor/get/service/category', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_service_category(self, **post):
        category_id = request.env['product.category'].sudo().search_read(
            [], ['name', 'id'])
        if category_id:
            category_id = self.get_list_with_image(category_id, 'product.category', 'image_1920')
            return valid_response({'result': category_id}, message='Service Category Fetched Successfully !',
                                  is_http=False)
        else:
            return valid_response({'result': False}, message='Service Category Fetching Failed !',
                                  is_http=False)

    @http.route('/vendor/submit/service/details', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_submit_service_details(self, **post):
        data = json.loads(request.httprequest.data)
        name = data.get('name', False)
        internal_reference = data.get('reference', False)
        cost = data.get('cost', False)
        sales_price = data.get('sales_price', False)
        category = data.get('category', False)
        description_sale = data.get('description', False)
        user = data.get('user', False)
        values = {'name': name, 'standard_price': cost, 'lst_price': sales_price, 'categ_id': category,
                  'kg_partner_id': user}
        values['default_code'] = internal_reference if internal_reference else ''
        values['description_sale'] = description_sale if description_sale else ''
        product_id = request.env['product.product'].sudo().create(values)
        if product_id:
            return valid_response({'result': True}, message='Service Created Successfully !', is_http=False)

    @http.route('/vendor/get/pending/services', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_pending_services(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('state', '=', 'draft'), ('irono_service', '=', True), ('kg_vendor_id', '=', user)],
            ['id', 'name', 'partner_id', 'order_line', 'amount_total'])
        order_ids = self.get_list_with_orderlines(order_ids)
        return valid_response({'result': order_ids}, message='Pending Orders !',
                              is_http=False)

    @http.route('/vendor/get/accepted/services', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_accepted_services(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('state', '=', 'sale'), ('invoice_status', '!=', 'invoiced'), ('irono_service', '=', True),
             ('kg_vendor_id', '=', user)],
            ['id', 'name', 'partner_id', 'order_line', 'amount_total'])
        order_ids = self.get_list_with_orderlines(order_ids)
        return valid_response({'result': order_ids}, message='Accepted Orders !',
                              is_http=False)

    @http.route('/vendor/get/completed/services', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_completed_services(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('state', '=', 'sale'), ('invoice_status', '=', 'invoiced'), ('irono_service', '=', True),
             ('kg_vendor_id', '=', user)],
            ['id', 'name', 'partner_id', 'order_line', 'amount_total'])
        order_ids = self.get_list_with_orderlines(order_ids)
        return valid_response({'result': order_ids}, message='Completed Orders !',
                              is_http=False)


    ''' Functions '''

    def check_user_exist(self, phone):
        if phone:
            partner = request.env['res.partner'].sudo().search(
                [('phone', '=', phone), ('kg_partner_type', '=', 'vendor'), ('active', '=', True)])
            return partner
        else:
            return False

    def check_sleeping_user_exist(self, phone):
        if phone:
            partner = request.env['res.partner'].sudo().search(
                [('phone', '=', phone), ('kg_partner_type', '=', 'vendor'), ('active', '=', False)])
            return partner
        else:
            return False

    def generate_login_otp(self):
        return random.randint(1000, 9999)

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

    def check_user_otp(self, phone, otp):
        partner_id = self.check_user_exist(phone)
        if partner_id and partner_id.kg_otp:
            if partner_id.kg_otp == otp:
                return partner_id
            return False
        else:
            partner_id = self.check_sleeping_user_exist(phone)
            if partner_id and partner_id.kg_otp:
                if partner_id.kg_otp == otp:
                    return partner_id
                return False

    def vendor_home_page_values(self, partner_id):
        if partner_id:
            values = {}
            values['user_name'] = partner_id.name if partner_id.name else ''
            values['user_id'] = partner_id.id
            values['user_type'] = partner_id.kg_partner_type if partner_id.kg_partner_type else ''
            if partner_id.kg_partner_type == 'vendor':
                banners = request.env['irono.banner'].sudo().search_read(
                    [('offers_for', '=', 'vendor'), ('active', '=', True)],
                    ['name', 'id', 'background_color', 'sub_heading', 'main_heading', 'button_text', 'product_id'])
                banners = self.get_list_with_image(banners, 'irono.banner', 'background_image')
                services_providered = request.env['product.product'].sudo().search_read(
                    [('kg_partner_id', '=', partner_id.id)], ['name', 'id', 'lst_price'])
                services_providered = self.get_list_with_image(services_providered, 'product.product', 'image_1920')
                values['banners'] = banners
                values['services_providered'] = services_providered
            return values

    def get_list_with_image(self, values, model, field):
        if not values:
            return []
        for rec in values:
            rec['image'] = self.get_image_url(model, rec.get('id'), field)
        return values

    def get_image_url(self, resModel, resId, resField):
        IrConfig = request.env['ir.config_parameter'].sudo()
        base_url = IrConfig.get_param('report.url') or IrConfig.get_param('web.base.url')
        url = str(base_url) + str('/web/image?model=' + str(resModel if resModel else "") + '&id=' + str(
            resId if resId else "") + '&field=' + str(resField if resField else ""))
        return url

    def get_partner(self, id):
        return request.env['res.partner'].sudo().browse(int(id))

    def get_orderline(self, id):
        return request.env['sale.order.line'].sudo().browse(int(id))

    def get_list_with_orderlines(self, saleorder):
        if saleorder:
            for rec in saleorder:
                orderlines_list = []
                for line in rec.get('order_line'):
                    orders = self.get_orderline(line)
                    orderlines_list.append(
                        {'id': orders.id, 'product': orders.product_id.name, 'qty': orders.product_uom_qty,
                         'unit_price': orders.price_unit, 'total_amount': orders.price_total})
                rec['order_line'] = orderlines_list
            return saleorder
        else:
            return saleorder
