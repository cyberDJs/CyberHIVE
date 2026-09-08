#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import os
import sys
import unittest.mock
from http import HTTPStatus
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'infra/live-usb/debian-live/config/includes.chroot/usr/local/bin/cyberhive-web'

os.environ['CYBERHIVE_TAILSCALE_HOSTNAME'] = 'cyberhive-test'
loader = importlib.machinery.SourceFileLoader('cyberhive_web_pairing_limit_test', str(WEB))
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
with unittest.mock.patch('pathlib.Path.mkdir'), \
     unittest.mock.patch('pathlib.Path.write_text'), \
     unittest.mock.patch('os.chmod'):
    loader.exec_module(module)

class Headers(dict):
    def get(self, key, default=None):
        return super().get(key, default)

class PairFile:
    def read_text(self, *args, **kwargs):
        return '000000'

def pair_attempt(peer):
    handler = object.__new__(module.Handler)
    handler.path = '/api/pair'
    handler.client_address = (peer, 45678)
    handler.headers = Headers({'Host': 'cyberhive.local', 'Content-Type': 'application/json'})
    handler.status = None
    handler.payload = None

    def send_json(status, payload, extra_headers=None):
        handler.status = status
        handler.payload = payload

    handler.send_json = send_json
    handler.read_json_body = lambda: {'code': '111111'}
    module.PAIR_FILE = PairFile()
    handler.do_POST()
    return handler.status, handler.payload

module.ATTEMPTS.clear()
module.GLOBAL_ATTEMPTS.clear()

limit = module.PAIRING_GLOBAL_ATTEMPT_LIMIT
for index in range(limit):
    status, payload = pair_attempt(f'192.168.55.{index + 1}')
    assert status == HTTPStatus.UNAUTHORIZED, (index, status, payload)

status, payload = pair_attempt('192.168.55.250')
assert status == HTTPStatus.TOO_MANY_REQUESTS, (status, payload)
assert payload == {'error': 'pairing rate limit exceeded'}, payload
print('CyberHIVE web pairing global limit behavior passed')
