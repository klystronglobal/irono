import base64
import datetime
import json
import logging

import werkzeug

from odoo import _
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

DB_NAME = ""
ROUTE_BASE = "/api/"


def default(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, bytes):
        return str(o)


def get_user(user):
    if not user:
        raise UserError(_("Required parameter 'user_id' is missing."))
    if not isinstance(user, int):
        if user.isdigit():
            user_id = int(user)
        else:
            raise UserError(_("The given value %s for user_id is not valid.") % user)
    else:
        user_id = user
    return request.env['res.users'].sudo().browse(user_id)


def convert_image_to_url(model, field_name, rec_id):
    url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    image_url = "%s/web/image?model=%s&field=%s&id=%s" % (url, model, field_name, rec_id)
    return image_url

def valid_response(result, message='Successful', status_code=200, is_http=False):
    """Valid Response
    This will be return when the http request was successfully processed."""
    data = {
        "message": message,
        "status": True,
        "status_code": status_code,
        "data": result,
    }
    if is_http:
        return werkzeug.wrappers.Response(
            status=status_code, content_type="application/json; charset=utf-8",
            response=json.dumps(data, default=default),
        )
    return {
        "message": message,
        "status": True,
        "status_code": status_code,
        "data": result,
    }


def invalid_response(error_type, error=None, status_code=401, is_http=False):
    """Invalid Response
    This will be the return value whenever the server runs into an error
    either from the client or the server."""
    if is_http:
        return werkzeug.wrappers.Response(
            status=status_code,
            content_type="application/json; charset=utf-8",
            response=json.dumps(
                {
                    "error_type": error_type or 'Error/Exception',
                    "error": str(error) if error else "Wrong arguments (missing validation)",
                    "message": "Something went wrong.",
                    "status": False,
                    "status_code": status_code,
                },
                default=datetime.datetime.isoformat,
            ),
        )
    return {
        "error": str(error) if error else "Wrong arguments (missing validation)",
        "error_type": error_type or '',
        "message": "Something went wrong.",
        "status": False,
        "status_code": status_code,
    }


def extract_arguments(limit="80", offset=0, order="id", domain="", fields=[]):
    """Parse additional data sent along request."""
    limit = int(limit)
    expr = []
    if domain:
        expr = [tuple(preg.replace(":", ",").split(",")) for preg in domain.split(",")]
        expr = json.dumps(expr)
        expr = json.loads(expr, parse_int=True)
    if fields:
        fields = fields.split(",")

    if offset:
        offset = int(offset)
    return [expr, fields, offset, limit, order]


def _convert_image_to_base64(bite_string):
    if bite_string:
        converted = bite_string.decode('utf-8')
        return converted
    return ''
