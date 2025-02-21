# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import http
import json, random, logging
from odoo.http import request
from twilio.rest import Client
from bs4 import BeautifulSoup
from twilio.base.exceptions import TwilioException
from odoo.addons.kg_irono_mobile_api.common import (valid_response, invalid_response, ROUTE_BASE, get_user)

_logger = logging.getLogger(__name__)


class IronoVendor(http.Controller):

    @http.route('/get/irono/image/<string:model>/<int:id>/<string:field>', type='http', auth="public")
    def get_images_view(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                        filename_field='name', filename=None, mimetype=None, unique=False,
                        download=False, width=0, height=0, crop=False, access_token=None,
                        nocache=False):
        record = request.env[model].sudo().browse(int(id))
        stream = request.env['ir.binary']._get_image_stream_from(
            record, field, filename=filename, filename_field=filename_field,
            mimetype=mimetype, width=int(width), height=int(height), crop=crop,
        )
        send_file_kwargs = {'as_attachment': download}
        if unique:
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs['max_age'] = None

        res = stream.get_response(**send_file_kwargs)
        res.headers['Content-Security-Policy'] = "default-src 'none'"
        return res

    @http.route('/vendor/login', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_login_phone(self, **post):
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
        self.send_login_otp(login_otp, phone)
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
                                      message='Please Submit Bussiness Related Documents !', is_http=False)
            if result.verified_vendor == 'pending':
                return valid_response({'result': 'pending', 'user': result.id},
                                      message='Verification Pending !', is_http=False)
            values = self.vendor_home_page_values(result)
            return valid_response(values, message='User Authentication Successfull !', is_http=False)
        else:
            return valid_response({'result': False}, message='User Authentication Failed !', is_http=False)

    @http.route('/vendor/get/home/page/values', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_homepage_values(self, **post):
        data = json.loads(request.httprequest.data)
        phone = data.get('phone', False)
        result = self.check_user_exist(phone)
        values = self.vendor_home_page_values(result)
        return valid_response(values, message='User Authentication Successfull !',
                              is_http=False)

    @http.route('/vendor/submit/bussiness/details', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_submit_bussiness_details(self, **post):
        data = json.loads(request.httprequest.data)
        bussiness_name = data.get('name', False)
        bussiness_phone = data.get('phone', False)
        bussiness_email = data.get('email', False)
        bussiness_image = data.get('image', False)
        bussiness_document = data.get('document', False)
        user = data.get('user', False)
        partner_id = self.get_partner(user)
        if partner_id:
            partner_id.write({'bussiness_name': bussiness_name, 'bussiness_phone': bussiness_phone,
                              'bussiness_email': bussiness_email, 'verified_vendor': 'pending',
                              'bussiness_image': bussiness_image, 'bussiness_document': bussiness_document})
            return valid_response({'result': True}, message='Bussiness Details Submitted Successfull !', is_http=False)

    @http.route('/vendor/get/service/category', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_service_category(self, **post):
        category_id = request.env['product.category'].sudo().search_read(
            [('irono_service', '=', True)], ['name', 'id'])
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
                  'kg_partner_id': user, 'irono_service': True, 'detailed_type': 'service'}
        values['default_code'] = internal_reference if internal_reference else ''
        values['description_sale'] = description_sale if description_sale else ''
        product_id = request.env['product.product'].sudo().create(values)
        if product_id:
            return valid_response({'result': True}, message='Service Created Successfully !', is_http=False)

    @http.route('/vendor/get/service/details', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_service_details(self, **post):
        data = json.loads(request.httprequest.data)
        product_id = data.get('product_id', False)
        user = data.get('user', False)
        if product_id:
            product = request.env['product.product'].sudo().search(
                [('id', '=', product_id), ('kg_partner_id', '=', user)])
        if product:
            values = {'name': product.name, 'standard_price': product.standard_price, 'lst_price': product.lst_price,
                      'categ_id': product.categ_id.name,
                      'reference_no': product.default_code}
            return valid_response(values, message='Service Details Fetched Successfully !', is_http=False)
        return valid_response({'result': False}, message='Service Details Fetching Failed !', is_http=False)

    @http.route('/vendor/update/service/details', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_update_service_details(self, **post):
        data = json.loads(request.httprequest.data)
        product_id = data.get('product_id', False)
        name = data.get('name', False)
        standard_price = data.get('standard_price', False)
        lst_price = data.get('lst_price', False)
        categ_id = data.get('categ_id', False)
        reference_no = data.get('reference_no', False)
        user = data.get('user', False)
        if product_id:
            product = request.env['product.product'].sudo().search(
                [('id', '=', product_id), ('kg_partner_id', '=', user)])
        if product:
            company = request.env['res.company'].sudo().search([], limit=1)
            values = {'name': name, 'standard_price': standard_price, 'lst_price': lst_price,
                      'categ_id': categ_id, 'default_code': reference_no, 'company_id': company.id}
            # Issue #####################################################
            product_new = product.sudo().write(values)
            if product_new:
                return valid_response(values, message='Service Details Updated Successfully !', is_http=False)
        return valid_response({'result': False}, message='Service Details Updating Failed !', is_http=False)

    @http.route('/vendor/get/pending/services', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_pending_services(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('state', '=', 'draft'), ('irono_service', '=', True), ('kg_vendor_id', '=', user)],
            ['id', 'name', 'partner_id', 'order_line', 'amount_total'])
        order_ids = self.get_list_with_orderlines(order_ids)
        order_ids = self.image_for_orders(order_ids,user)
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
        order_ids = self.image_for_orders(order_ids,user)
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
        order_ids = self.image_for_orders(order_ids,user)
        return valid_response({'result': order_ids}, message='Completed Orders !',
                              is_http=False)

    @http.route('/vendor/get/order/form', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_order_form(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        order_id = data.get('order_id', False)
        order_ids = request.env['sale.order'].sudo().search_read(
            [('id', '=', int(order_id))], ['id', 'name', 'partner_id', 'order_line', 'amount_total'])
        order_ids = self.get_list_with_orderlines(order_ids)
        order_ids = self.image_for_orders(order_ids,user)
        return valid_response({'result': order_ids}, message='Order Details !',
                              is_http=False)

    @http.route('/vendor/submit/accept/order', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_submit_accept_order(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        order_id = data.get('order_id', False)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        partner = request.env['res.partner'].sudo().browse(int(user))
        if order and partner:
            order.sudo().with_user(request.env['res.users'].sudo().browse(2)).action_confirm()
            sub_type = request.env['mail.message.subtype'].sudo().search([('name', '=', 'Note')], limit=1)
            message = request.env['mail.message'].sudo().create(
                {'body': 'Order accepted by ' + partner.name, 'irono_type': 'customer', 'model': 'sale.order',
                 'res_id': order.id, 'record_name': order.name, 'subject': 'Vendor: Accepted Order',
                 'author_id': partner.id, 'partner_ids': [order.partner_id.id], 'message_type': 'notification',
                 'subtype_id': sub_type.id, 'irono_service': True})
            return valid_response({'result': True}, message='Order Accepted !',
                                  is_http=False)
        return valid_response({'result': False}, message='Order Not Accepted !',
                              is_http=False)

    @http.route('/vendor/submit/complete/order', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_submit_complete_order(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        order_id = data.get('order_id', False)
        otp = data.get('otp', False)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        partner = request.env['res.partner'].sudo().browse(int(user))
        if order:
            if order.vendor_otp != otp:
                return valid_response({'result': False}, message='Incorrect OTP. Order Not Completed !',
                                      is_http=False)
            for rec in order.order_line:
                rec.sudo().write({'qty_delivered': rec.product_uom_qty})
            moves = order.sudo().with_user(request.env['res.users'].sudo().browse(2))._create_invoices()
            moves.sudo().with_user(request.env['res.users'].sudo().browse(2)).action_post()
            request.env['account.payment.register'].with_context(active_model='account.move',
                                                                 active_ids=moves.ids).with_user(
                request.env['res.users'].sudo().browse(2)).create({
                'payment_date': moves.date,
            }).with_user(request.env['res.users'].sudo().browse(2))._create_payments()
            sub_type = request.env['mail.message.subtype'].sudo().search([('name', '=', 'Note')], limit=1)
            message = request.env['mail.message'].sudo().create(
                {'body': 'Order completed by ' + partner.name, 'irono_type': 'customer', 'model': 'sale.order',
                 'res_id': order.id, 'record_name': order.name, 'subject': 'Vendor: Completed Order',
                 'author_id': partner.id, 'partner_ids': [order.partner_id.id], 'message_type': 'notification',
                 'subtype_id': sub_type.id, 'irono_service': True})
            return valid_response({'result': True}, message='Order Accepted !',
                                  is_http=False)
        return valid_response({'result': False}, message='Order Not Accepted !',
                              is_http=False)

    @http.route('/vendor/update/profile/details', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_update_profile_details(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        name = data.get('name', False)
        phone = data.get('phone', False)
        email = data.get('email', False)
        description = data.get('description', False)
        bussiness_name = data.get('bussiness_name', False)
        bussiness_phone = data.get('bussiness_phone', False)
        bussiness_email = data.get('bussiness_email', False)
        if user:
            partner = request.env['res.partner'].sudo().browse(int(user))
        if partner:
            values = {'name': name, 'phone': phone, 'email': email, 'description': description,
                      'bussiness_name': bussiness_name, 'bussiness_phone': bussiness_phone,
                      'bussiness_email': bussiness_email}
            partner.sudo().write(values)
            return valid_response(values, message='Vendor Profile Details Updated Successfully !', is_http=False)
        return valid_response({'result': False}, message='Vendor Profile Details Updating Failed !', is_http=False)

    @http.route('/vendor/get/profile/details', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_profile_details(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        if user:
            partner = request.env['res.partner'].sudo().browse(int(user))
        if partner:
            values = {'name': partner.name, 'email': partner.email, 'phone': partner.phone,
                      'bussiness_name': partner.bussiness_name, 'bussiness_phone': partner.bussiness_phone,
                      'bussiness_email': partner.bussiness_email, 'about': partner.description}
            values['image'] = self.get_image_url('res.partner', partner.id, 'image_1920')
            return valid_response(values, message='Vendor Profile Details Fetched Successfully !', is_http=False)
        return valid_response({'result': False}, message='Vendor Profile Details Fetching Failed !', is_http=False)

    @http.route('/vendor/get/notification', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_get_notification(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        messages = request.env['mail.message'].sudo().search_read(
            [('partner_ids', 'in', [user]), ('irono_service', '=', True), ('irono_type', '=', 'customer')],
            ['id', 'body'],
            order='id desc')
        messages = self.clean_mail_body(messages)
        return valid_response({'result': messages}, message='Vendor Notification Fetched Successfully !',
                              is_http=False)

    @http.route('/get/terms/and/condition', methods=["POST"], type="json", auth="none", csrf=False)
    def get_terms_and_conditions(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        terms_and_conditions = request.env['ir.config_parameter'].sudo().get_param(
            'kg_irono_mobile_api.terms_and_conditions_irono')
        return valid_response({'result': terms_and_conditions}, message='Terms and Conditions Fetched Successfully !',
                              is_http=False)

    @http.route('/get/privacy/and/policy', methods=["POST"], type="json", auth="none", csrf=False)
    def get_privacy_and_policy(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        privacy_and_policy = request.env['ir.config_parameter'].sudo().get_param(
            'kg_irono_mobile_api.privacy_and_policy_irono')
        return valid_response({'result': privacy_and_policy}, message='Privacy and Policy Fetched Successfully !',
                              is_http=False)

    # @http.route('/get/contact/us', methods=["POST"], type="json", auth="none", csrf=False)
    # def get_contact_us(self, **post):
    #     data = json.loads(request.httprequest.data)
    #     user = data.get('user', False)
    #     company = request.env['res.company'].sudo().search([], limit=1)
    #     name = company.name
    #     phone = company.phone
    #     street = company.street
    #     street2 = company.street2
    #     city = company.city
    #     zip = company.zip
    #     email = company.zip
    #     website = company.website
    #     state = company.state_id.name if company.state_id else ''
    #     country = company.country_id.name if company.country_id else ''
    #     values = {'name': name, 'phone': phone, 'street': street, 'street2': street2, 'city': city, 'zip': zip,
    #               'email': email, 'website':website,'state':state,'country':country}
    #     return valid_response({'result': values}, message='Company Details Fetched Successfully !',
    #                           is_http=False)

    @http.route('/submit/contact/us', methods=["POST"], type="json", auth="none", csrf=False)
    def submit_contact_us(self, **post):
        data = json.loads(request.httprequest.data)
        user = data.get('user', False)
        name = data.get('subject', False)
        description = data.get('description', False)
        priority = data.get('priority', False)
        try:
            company = request.env['res.company'].sudo().search([], limit=1)
            partner = request.env['res.partner'].sudo().browse(int(user))
            team_id = request.env['helpdesk.ticket.team'].sudo().search([('name', '=', 'Helpdesk')], limit=1)
            values = {'name': name, 'description': description, 'priority': str(priority), 'company_id': company.id,
                      'partner_id': partner.id, 'partner_name': partner.name, 'partner_email': partner.email,
                      'team_id': team_id.id, 'user_id': 2,'channel_id':1}
            ticket = request.env['helpdesk.ticket'].sudo().with_user(request.env['res.users'].sudo().browse(2)).create(values)
            return valid_response({'result': True}, message='Ticket Raised Successfully !',
                                  is_http=False)
        except:
            return valid_response({'result': False}, message='Ticketing Failed !',
                                  is_http=False)

    @http.route('/vendor/submit/feedback', methods=["POST"], type="json", auth="none", csrf=False)
    def vendor_submit_feedback(self, **post):
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
            return valid_response({'result': True}, message='Vendor Feedback Submitted Successfully !',
                                  is_http=False)
        except:
            return valid_response({'result': False}, message='Vendor Feedback Submitting Failed !',
                                  is_http=False)

    ''' Functions '''

    def image_for_orders(self, values,user):
        for rec in values:
            rec['image'] = self.get_image_url('res.partner', user, 'image_1920')
        return values

    def clean_mail_body(self, data):
        for rec in data:
            rec['body'] = BeautifulSoup(rec['body'], "lxml").text
        return data

    def check_user_exist(self, phone):
        if phone:
            partner = request.env['res.partner'].sudo().search(
                [('phone', '=', phone), ('kg_partner_type', '=', 'vendor'), ('active', '=', True)], limit=1)
            return partner
        else:
            return False

    def check_sleeping_user_exist(self, phone):
        if phone:
            partner = request.env['res.partner'].sudo().search(
                [('phone', '=', phone), ('kg_partner_type', '=', 'vendor'), ('active', '=', False)], limit=1)
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
        url = str(base_url) + str('/get/irono/image/' + str(resModel if resModel else "") + '/' + str(
            resId if resId else "") + '/' + str(resField if resField else ""))
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
