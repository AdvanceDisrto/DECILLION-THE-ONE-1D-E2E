import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from decillion_one import execute, sign, verify


class Provider(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        response = {'request_id': body['request_id'], 'output': 'provider response'}
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_):
        pass


class E2ETests(unittest.TestCase):
    def test_no_provider_is_not_inference(self):
        receipt = execute('hello')
        self.assertEqual(receipt['evidence']['outcome']['status'], 'not_executed')
        self.assertIsNone(receipt['evidence']['outcome']['output'])
        self.assertEqual(receipt['evidence']['verification'], 'not_verified')
        self.assertTrue(verify(receipt))

    def test_explicit_local_provider(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            receipt = execute('hello', endpoint=f'http://127.0.0.1:{server.server_port}/infer')
            self.assertEqual(receipt['evidence']['outcome']['status'], 'completed')
            self.assertEqual(receipt['evidence']['outcome']['output'], 'provider response')
            self.assertEqual(receipt['evidence']['model_identity'], 'unverified')
            self.assertTrue(verify(receipt))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_tampering_detected(self):
        receipt = execute('hello')
        receipt['evidence']['request']['prompt'] = 'changed'
        self.assertFalse(verify(receipt))

    def test_optional_signature_requires_key(self):
        signed = sign(execute('hello'), b'test-key')
        self.assertTrue(verify(signed, b'test-key'))
        self.assertFalse(verify(signed))
        self.assertFalse(verify(signed, b'wrong-key'))
        self.assertEqual(signed['evidence']['verification'], 'not_verified')

    def test_reject_remote_plaintext(self):
        with self.assertRaises(ValueError):
            execute('hello', endpoint='http://example.com/infer')

    def test_empty_prompt(self):
        with self.assertRaises(ValueError):
            execute('  ')


if __name__ == '__main__':
    unittest.main()
