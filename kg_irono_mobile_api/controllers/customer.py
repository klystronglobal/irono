# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import http
import json, random, logging
from bs4 import BeautifulSoup
from odoo.http import request
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from odoo.addons.kg_irono_mobile_api.common import (valid_response, invalid_response, ROUTE_BASE, get_user)

_logger = logging.getLogger(__name__)


class IronoCustomer(http.Controller):

    @http.route('/customer/login', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_login_phone(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        partner_id = self.check_user_exist(phone)
        if partner_id:
            _logger.info("Already a user")
            login_otp = self.generate_login_otp()
            partner_id.sudo().write({'kg_otp': login_otp})
            self.send_login_otp(login_otp, phone)
            return valid_response({'result': True}, message='User Already Exists. Provide OTP !',
                                  is_http=False)
        else:
            return valid_response({'result': False}, message='User does not exists. Sign Up !',
                                  is_http=False)

    @http.route('/customer/sign/up', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_sign_up(self, **post):
        data = json.loads(request.httprequest.data)
        values = {'kg_partner_type': 'customer', 'active': False}
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
        self.send_login_otp(login_otp, phone)
        return valid_response({'result': True}, message='Customer details saved. Waiting for otp.',
                              is_http=False)

    @http.route('/customer/submit/otp', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_login_otp(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        otp = data.get('otp', False)
        result = self.check_user_otp(phone, int(otp))
        if result:
            if not result.active:
                result.write({'active': True})
            values = self.customer_home_page_values(result)
            return valid_response(values, message='User Authentication Successfull !',
                                  is_http=False)
        else:
            return valid_response({'result': False}, message='User Authentication Failed !',
                                  is_http=False)

    @http.route('/customer/get/home/page/values', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_homepage_values(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        result = self.check_user_exist(phone)
        if not result:
            return valid_response({'result': False}, message='User Does not Exist !',
                                  is_http=False)
        values = self.customer_home_page_values(result)
        return valid_response(values, message='User Authentication Successfull !',
                              is_http=False)

    @http.route('/customer/get/vendor/service/details', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_vendor_service_details(self, **post):
        data = json.loads(request.httprequest.data)
        service = data.get('service', False)
        values = {}
        vendor_id = request.env['res.partner'].sudo().browse(int(service))
        if vendor_id:
            values['name'] = vendor_id.name
            values['id'] = vendor_id.id
            values['about'] = vendor_id.description
            values['image'] = self.get_image_url('res.partner', vendor_id.id, 'image_1920')
            values['services'] = request.env['product.product'].sudo().search_read(
                [('kg_partner_id', '=', vendor_id.id)], ['name', 'id', 'lst_price'])
            return valid_response(values, message='Service Details Fetched',
                                  is_http=False)
        return valid_response({'result': False}, message='Service Details Failed To Fetch',
                              is_http=False)

    @http.route('/customer/book/service', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_book_service(self, **post):
        data = json.loads(request.httprequest.data)
        customer_id = data.get('customer', False)
        vendor_id = data.get('vendor', False)
        services_ids = data.get('services', False)
        notes = data.get('notes', False)
        delivery_date = data.get('delivery_date', False)
        try:
            # datetime_str = '09/19/22 13:55:26'
            datetime_object = datetime.strptime(delivery_date, '%m/%d/%y %H:%M:%S')
            company_id = request.env['res.company'].sudo().search([], limit=1)
            partner = request.env['res.partner'].sudo().browse(int(customer_id))
            order_lines = []
            for rec in services_ids:
                order_lines.append((0, 0, {'product_id': rec['id'], 'product_uom_qty': rec['qty']}))
            order_id = request.env['sale.order'].sudo().create(
                {'partner_id': customer_id, 'irono_service': True, 'order_line': order_lines, 'note': notes,
                 'commitment_date': datetime_object,
                 'company_id': company_id.id, 'kg_vendor_id': vendor_id})
            sub_type = request.env['mail.message.subtype'].sudo().search([('name', '=', 'Note')], limit=1)
            message = request.env['mail.message'].sudo().create(
                {'body': 'New service requested by ' + partner.name, 'irono_type': 'customer', 'model': 'sale.order',
                 'res_id': order_id.id, 'record_name': order_id.name, 'subject': 'Customer: Requested Order',
                 'author_id': partner.id, 'partner_ids': [vendor_id], 'message_type': 'notification',
                 'subtype_id': sub_type.id,
                 'irono_service': True})
            _logger.info("Created a order...")
            return valid_response({'result': True}, message='Order Booked Successfully !',
                                  is_http=False)
        except:
            return valid_response({'result': False}, message='Order Booking Failed !',
                                  is_http=False)

    @http.route('/customer/get/pending/services', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_pending_services(self, **post):
        data = json.loads(request.httprequest.data)
        customer_id = data.get('customer', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('state', '=', 'draft'), ('irono_service', '=', True), ('partner_id', '=', customer_id)],
            ['id', 'name', 'kg_vendor_id', 'amount_total'])
        order_ids = self.image_for_orders(order_ids)
        return valid_response({'result': order_ids}, message='Pending Orders !',
                              is_http=False)

    @http.route('/customer/get/accepted/services', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_accepted_services(self, **post):
        data = json.loads(request.httprequest.data)
        customer_id = data.get('customer', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('state', '=', 'sale'), ('invoice_status', '!=', 'invoiced'), ('irono_service', '=', True),
             ('partner_id', '=', customer_id)],
            ['id', 'name', 'kg_vendor_id', 'amount_total', 'vendor_otp'])
        order_ids = self.image_for_orders(order_ids)
        return valid_response({'result': order_ids}, message='Accepted Orders !',
                              is_http=False)

    @http.route('/customer/get/completed/services', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_completed_services(self, **post):
        data = json.loads(request.httprequest.data)
        customer_id = data.get('customer', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('state', '=', 'sale'), ('invoice_status', '=', 'invoiced'), ('irono_service', '=', True),
             ('partner_id', '=', customer_id)],
            ['id', 'name', 'kg_vendor_id', 'amount_total'])
        order_ids = self.image_for_orders(order_ids)
        return valid_response({'result': order_ids}, message='Completed Orders !',
                              is_http=False)

    @http.route('/customer/get/profile/details', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_profile_details(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        if user:
            partner = request.env['res.partner'].sudo().browse(int(user))
        if partner:
            values = {'name': partner.name, 'email': partner.email, 'phone': partner.phone}
            values['image'] = self.get_image_url('res.partner', partner.id, 'image_1920')
            return valid_response(values, message='Vendor Profile Details Fetched Successfully !', is_http=False)
        return valid_response({'result': False}, message='Vendor Profile Details Fetching Failed !', is_http=False)

    @http.route('/customer/update/profile/details', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_update_profile_details(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        name = data.get('name', False)
        phone = data.get('phone', False)
        email = data.get('email', False)
        if user:
            partner = request.env['res.partner'].sudo().browse(int(user))
        if partner:
            values = {'name': name, 'phone': phone, 'email': email}
            partner.sudo().write(values)
            return valid_response(values, message='Customer Profile Details Updated Successfully !', is_http=False)
        return valid_response({'result': False}, message='Customer Profile Details Updating Failed !', is_http=False)

    @http.route('/customer/get/notification', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_notification(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        messages = request.env['mail.message'].sudo().search_read(
            [('partner_ids', 'in', [user]), ('irono_service', '=', True), ('irono_type', '=', 'customer')],
            ['id', 'body'],
            order='id desc')
        messages = self.clean_mail_body(messages)
        return valid_response({'result': messages}, message='Customer Notification Fetched Successfully !',
                              is_http=False)

    @http.route('/customer/get/category/wise/services', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_get_category_wise_service(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        category_id = data.get('category_id', False)
        values = []
        providers = []
        try:
            product_ids = request.env['product.product'].sudo().search_read(
                [('categ_id', '=', int(category_id)), ('irono_service', '=', True), ('kg_partner_id', '!=', False)],['kg_partner_id'])
            print(product_ids,'product_idsproduct_ids')
            for rec in product_ids:
                if rec.get('kg_partner_id')[0] not in providers:
                    providers.append(rec.get('kg_partner_id')[0])
            service_providers = request.env['res.partner'].sudo().browse(providers)
            for rec in service_providers:
                values.append({'id':rec.id,'name':rec.name})
            values = self.get_list_with_image(values, 'res.partner', 'image_1920')
            return valid_response({'result': values}, message='Category Wise Product Fetched Successfully !',
                                  is_http=False)
        except:
            return valid_response({'result': False}, message='Category Wise Product Fetching Failed !',
                                  is_http=False)

    @http.route('/customer/submit/global/search', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_submit_global_search(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        search = data.get('search', False)
        values = []
        try:
            partner_ids = request.env['res.partner'].sudo().search(
                ['|', '|', ('name', 'ilike', str(search)), ('phone', 'ilike', str(search)),
                 ('bussiness_name', 'ilike', str(search)), ('kg_partner_type', '=', 'vendor')])
            product_ids = request.env['product.product'].sudo().search(
                ['|', ('name', 'ilike', str(search)), ('default_code', 'ilike', str(search)),
                 ('irono_service', '=', True)])
            for rec in partner_ids:
                values.append({'name': rec.name, 'id': rec.id})
            for rec in product_ids:
                values.append({'name': rec.kg_partner_id.name, 'id': rec.kg_partner_id.id})
            values = self.remove_duplicates(values)
            values = self.get_list_with_image(values, 'res.partner', 'image_1920')
            return valid_response({'result': values}, message='Search Result Fetched Successfully !',
                                  is_http=False)
        except:
            return valid_response({'result': False}, message='Search Result Fetching Failed !',
                                  is_http=False)

    @http.route('/customer/submit/feedback', methods=["POST"], type="json", auth="none", csrf=False)
    def customer_submit_feedback(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        message = data.get('message', False)
        try:
            partner = request.env['res.partner'].sudo().browse(int(user))
            admin = request.env['res.partner'].sudo().browse(int(3))
            sub_type = request.env['mail.message.subtype'].sudo().search([('name', '=', 'Discussions')], limit=1)
            message = request.env['mail.message'].sudo().create(
                {'body': message, 'model': 'res.partner',
                 'res_id': partner.id, 'record_name': partner.name, 'subject': partner.name,
                 'author_id': partner.id, 'partner_ids': [admin.id], 'message_type': 'comment',
                 'subtype_id': sub_type.id})
            return valid_response({'result': True}, message='Customer Feedback Submitted Successfully !',
                                  is_http=False)
        except:
            return valid_response({'result': False}, message='Customer Feedback Submitting Failed !',
                                  is_http=False)

    '''  Functions  '''

    def clean_mail_body(self, data):
        for rec in data:
            rec['body'] = BeautifulSoup(rec['body'], "lxml").text
        return data

    def image_for_orders(self, values):
        for rec in values:
            rec['image'] = self.get_image_url('res.partner', rec.get('kg_vendor_id')[0], 'image_1920')
        return values

    def remove_duplicates(self, data):
        seen_ids = set()
        result = []
        for item in data:
            if item['id'] not in seen_ids:
                result.append(item)
                seen_ids.add(item['id'])
        return result

    def customer_home_page_values(self, partner_id):
        if partner_id:
            values = {}
            values['user_name'] = partner_id.name if partner_id.name else ''
            values['user_id'] = partner_id.id
            values['user_type'] = partner_id.kg_partner_type if partner_id.kg_partner_type else ''
            if partner_id.kg_partner_type == 'customer':
                banners = request.env['irono.banner'].sudo().search_read(
                    [('offers_for', '=', 'customer'), ('active', '=', True)],
                    ['name', 'id', 'background_color', 'sub_heading', 'main_heading', 'button_text', 'product_id'])
                services_providered = request.env['res.partner'].sudo().search_read(
                    [('kg_partner_type', '=', 'vendor')], ['name', 'id'])
                services_providered = self.get_list_with_image(services_providered, 'res.partner', 'image_1920')
                banners = self.get_list_with_image(banners, 'irono.banner', 'background_image')
                service_category = request.env['product.category'].sudo().search_read([('irono_service', '=', True)],
                                                                                      ['name', 'id'])
                service_category = self.get_list_with_image(service_category, 'product.category', 'image_1920')
                values['service_providers'] = services_providered
                values['service_categories'] = service_category
                values['banners'] = banners
            return values

    def check_user_exist(self, phone):
        if phone:
            partner = request.env['res.partner'].sudo().search(
                [('phone', '=', phone), ('kg_partner_type', '=', 'customer'), ('active', '=', True)], limit=1)
            return partner
        else:
            return False

    def check_sleeping_user_exist(self, phone):
        if phone:
            partner = request.env['res.partner'].sudo().search(
                [('phone', '=', phone), ('kg_partner_type', '=', 'customer'), ('active', '=', False)], limit=1)
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
            partner_id = self.check_sleeping_user_exist(phone)
            if partner_id and partner_id.kg_otp:
                if partner_id.kg_otp == otp:
                    return partner_id
                return False

    def get_list_with_image(self, values, model, field):
        if not values:
            return []
        for rec in values:
            rec['image'] = self.get_image_url(model, rec.get('id'), field)
        return values

    def get_image_url(self, resModel, resId, resField):
        IrConfig = request.env['ir.config_parameter'].sudo()
        base_url = IrConfig.get_param('report.url') or IrConfig.get_param('web.base.url')
        url = str(base_url) + str('/get/irono/image/' + str(resModel if resModel else "") + '/' + str(
            resId if resId else "") + '/' + str(resField if resField else ""))
        return url
