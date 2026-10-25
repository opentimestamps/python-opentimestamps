# Copyright (C) 2016 The OpenTimestamps developers
#
# This file is part of python-opentimestamps.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-opentimestamps including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.

import http.server
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

from opentimestamps.calendar import *
from opentimestamps.calendar import _SameHostHttpsRedirectHandler
from opentimestamps.core.notary import PendingAttestation
from opentimestamps.core.op import OpAppend
from opentimestamps.core.serialize import BytesSerializationContext, TrailingGarbageError
from opentimestamps.core.timestamp import Timestamp

class Test_UrlWhitelist(unittest.TestCase):
    def test_empty(self):
        """Empty whitelist"""
        wl = UrlWhitelist()

        self.assertNotIn('', wl)
        self.assertNotIn('http://example.com', wl)

    def test_exact_match(self):
        """Exact match"""

        wl = UrlWhitelist(("https://example.com",))
        self.assertIn("https://example.com", wl)
        self.assertNotIn("http://example.com", wl)
        self.assertNotIn("http://example.org", wl)

        # I'm happy for this to be strict
        self.assertIn("https://example.com", wl)

    def test_add_scheme(self):
        """URL scheme added automatically"""
        wl = UrlWhitelist(("example.com",))
        self.assertIn("https://example.com", wl)
        self.assertIn("http://example.com", wl)

    def test_port(self):
        """Ports must match, and be parseable"""
        wl = UrlWhitelist(("https://*.example.com:8080",))
        self.assertIn("https://foo.example.com:8080", wl)
        self.assertNotIn("https://foo.example.com", wl)
        self.assertNotIn("https://foo.example.com:8081", wl)

        wl = UrlWhitelist(("*.example.com",))
        self.assertNotIn("https://foo.example.com:8080", wl)
        self.assertNotIn("https://evil.com:.example.com", wl)
        self.assertNotIn("https://evil.com:80.example.com", wl)

    def test_invalid_pattern(self):
        """Patterns need a host and a numeric port"""
        for url in ("https://", "https://*.example.com:*", "https://example.com:80x"):
            with self.assertRaises(ValueError):
                UrlWhitelist((url,))

    def test_glob_match(self):
        """Glob matching"""
        wl = UrlWhitelist(("*.example.com",))
        self.assertIn("https://foo.example.com", wl)
        self.assertIn("http://bar.example.com", wl)
        self.assertIn("http://foo.bar.example.com", wl)

        self.assertNotIn("http://barexample.com", wl)


class Test_RemoteCalendar(unittest.TestCase):
    COMMITMENT = b'\xaa' * 32

    def serve(self, body, location=None):
        """Serve body, or redirect to location, in which {port} is the port served on"""
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if location is not None:
                    self.send_response(302)
                    self.send_header('Location', location.format(port=self.server.server_address[1]))
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_POST = do_GET

        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return RemoteCalendar('http://127.0.0.1:%d/' % server.server_address[1])

    def serialize(self, appends=0):
        t = Timestamp(self.COMMITMENT)
        for i in range(appends):
            t.ops.add(OpAppend(bytes([i]) * 1000)).attestations.add(PendingAttestation(''))
        if not appends:
            t.attestations.add(PendingAttestation(''))
        ctx = BytesSerializationContext()
        t.serialize(ctx)
        return ctx.getbytes()

    def test_response(self):
        """Response within the size limit"""
        calendar = self.serve(self.serialize())
        self.assertEqual(calendar.get_timestamp(self.COMMITMENT).msg, self.COMMITMENT)

    def test_response_too_big(self):
        """Response over the size limit"""
        body = self.serialize(appends=12)
        self.assertGreater(len(body), MAX_RESPONSE_LENGTH)
        self.assertLess(len(body), 2 * MAX_RESPONSE_LENGTH)
        with self.assertRaisesRegex(Exception, 'size limit'):
            self.serve(body).get_timestamp(self.COMMITMENT)

    def test_response_trailing_garbage(self):
        """Response with trailing garbage"""
        with self.assertRaises(TrailingGarbageError):
            self.serve(self.serialize() + b'garbage').get_timestamp(self.COMMITMENT)

    def test_url_scheme(self):
        """Only http and https calendar URLs"""
        RemoteCalendar('http://example.com')
        RemoteCalendar('https://example.com')
        for url in ('file:///etc/passwd', 'ftp://example.com', 'example.com'):
            with self.assertRaises(ValueError):
                RemoteCalendar(url)

    def test_redirects(self):
        """Redirects only to https URLs on the same host"""
        handler = _SameHostHttpsRedirectHandler()
        req = urllib.request.Request('https://a.example.com/timestamp/00')
        def redirect(url):
            return handler.redirect_request(req, None, 302, 'Found', {}, url)

        self.assertIsNotNone(redirect('https://a.example.com/other'))
        self.assertIsNone(redirect('https://b.example.com/other'))
        self.assertIsNone(redirect('http://a.example.com/other'))
        self.assertIsNone(redirect('file:///etc/passwd'))

    def test_redirects_end_to_end(self):
        """The calendar refuses redirects to other hosts, to http and to file:"""
        # The target would answer with a valid proof, so a followed redirect
        # would succeed
        target = self.serve(self.serialize())
        target_port = urllib.parse.urlparse(target.url).port

        for location in ('http://localhost:%d/' % target_port,  # another host, and http
                         'https://localhost:%d/' % target_port,  # another host
                         'http://127.0.0.1:%d/' % target_port,  # the same host, but http
                         'file:///etc/passwd'):
            with self.subTest(location=location):
                with self.assertRaises(urllib.error.HTTPError):
                    self.serve(b'', location=location).get_timestamp(self.COMMITMENT)
                with self.assertRaises(urllib.error.HTTPError):
                    self.serve(b'', location=location).submit(self.COMMITMENT)

        # A redirect to https on the same host is followed. The server speaks
        # plain http, so the request fails in the TLS handshake and not with
        # the redirect status.
        for call in ('get_timestamp', 'submit'):
            with self.subTest(call=call):
                calendar = self.serve(b'', location='https://127.0.0.1:{port}/')
                with self.assertRaises(urllib.error.URLError) as cm:
                    getattr(calendar, call)(self.COMMITMENT)
                self.assertNotIsInstance(cm.exception, urllib.error.HTTPError)
