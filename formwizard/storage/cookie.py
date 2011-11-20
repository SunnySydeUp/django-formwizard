from __future__ import absolute_import, unicode_literals
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.utils import simplejson as json
from django.utils.hashcompat import sha_constructor
from django.utils.encoding import smart_str
from formwizard.storage import Storage
import hmac


class CookieStorage(Storage):
    """
    A storage that stores form data in a cookie given to the user. Files remain
    stored in the provided file storage.
    """
    # explicitly specifying the separators removes extraneous JSON whitespace
    encoder = json.JSONEncoder(separators=(',', ':'))

    def __init__(self, *args, **kwargs):
        super(CookieStorage, self).__init__(*args, **kwargs)
        self.key = ('%s|%s' % (self.namespace, self.name)).encode('utf-8')

    def process_request(self, request):
        self.decode(request.COOKIES.get(self.key, ''))

    def process_response(self, response):
        if self.steps or self.current_step:
            response.set_cookie(self.key, self.encode())

    def decode(self, data):
        # check integrity
        hmac, _, payload = data.partition('$')
        if payload:
            if hmac != self.hmac(payload):
                raise SuspiciousOperation('Form wizard cookie manipulated')
            decoded = json.loads(payload, cls=json.JSONDecoder)
        else:
            decoded = {'current_step': None, 'steps': {}}
        super(CookieStorage, self).decode(decoded)

    def encode(self):
        data = super(CookieStorage, self).encode()
        payload = self.encoder.encode(data)
        return '%s$%s' % (self.hmac(payload), payload)

    def hmac(self, data):
        key = b'%s$%s' % (settings.SECRET_KEY, self.key)
        msg = data.encode('utf-8')
        return hmac.new(key, msg, sha_constructor).hexdigest()
