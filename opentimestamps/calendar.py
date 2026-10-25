# Copyright (C) 2016-2018 The OpenTimestamps developers
#
# This file is part of python-opentimestamps.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-opentimestamps including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.

import binascii
import urllib.request
import fnmatch

from urllib.parse import urljoin, urlparse
from opentimestamps.core.timestamp import Timestamp
from opentimestamps.core.serialize import BytesDeserializationContext


def get_sanitised_resp_msg(exp):
    """Get the sanitise response messages from a calendar response

    Returns the sanitised message, with any character not in the whitelist replaced by '_'
    """

    # Note how new lines are _not_ allowed: this is important, as otherwise the
    # message could include a second line pretending to be something else.
    WHITELIST = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#-.,; '

    # Two lines of text
    raw_msg = bytearray(exp.read(160))

    for i in range(len(raw_msg)):
        if raw_msg[i] not in WHITELIST:
            raw_msg[i] = ord('_')

    return raw_msg.decode()


class CommitmentNotFoundError(KeyError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class _SameHostHttpsRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects only to https URLs on the same host"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old = urlparse(req.full_url)
        new = urlparse(newurl)
        if new.scheme != 'https' or new.hostname != old.hostname:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)

_opener = urllib.request.build_opener(_SameHostHttpsRedirectHandler)

MAX_RESPONSE_LENGTH = 10000

def _read_timestamp(resp, msg):
    # FIXME: Not a particularly nice way of handling this, but it'll do
    # the job for now.
    resp_bytes = resp.read(MAX_RESPONSE_LENGTH + 1)
    if len(resp_bytes) > MAX_RESPONSE_LENGTH:
        raise Exception("Calendar response exceeded size limit")

    ctx = BytesDeserializationContext(resp_bytes)
    timestamp = Timestamp.deserialize(ctx, msg)
    ctx.assert_eof()
    return timestamp


class RemoteCalendar:
    """Remote calendar server interface"""

    def __init__(self, url, user_agent="python-opentimestamps"):
        if not isinstance(url, str):
            raise TypeError("URL must be a string")
        if urlparse(url).scheme not in ('http', 'https'):
            raise ValueError("URL must be http or https")
        self.url = url

        self.request_headers = {"Accept": "application/vnd.opentimestamps.v1",
                                "User-Agent": user_agent}

    def submit(self, digest, timeout=None):
        """Submit a digest to the calendar

        Returns a Timestamp committing to that digest
        """
        req = urllib.request.Request(urljoin(self.url, 'digest'), data=digest, headers=self.request_headers)

        with _opener.open(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise Exception("Unknown response from calendar: %d" % resp.status)

            return _read_timestamp(resp, digest)

    def get_timestamp(self, commitment, timeout=None):
        """Get a timestamp for a given commitment

        Raises KeyError if the calendar doesn't have that commitment
        """
        req = urllib.request.Request(
            urljoin(self.url, 'timestamp/' + binascii.hexlify(commitment).decode('utf8')),
            headers=self.request_headers)
        try:
            with _opener.open(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return _read_timestamp(resp, commitment)

                else:
                    raise Exception("Unknown response from calendar: %d" % resp.status)
        except urllib.error.HTTPError as exp:
            if exp.code == 404:
                raise CommitmentNotFoundError(get_sanitised_resp_msg(exp))
            else:
                raise exp


class UrlWhitelist(set):
    """Glob-matching whitelist for URL's"""

    def __init__(self, urls=()):
        for url in urls:
            self.add(url)

    def add(self, url):
        if not isinstance(url, str):
            raise TypeError("URL must be a string")

        if url.startswith('http://') or url.startswith('https://'):
            parsed_url = urllib.parse.urlparse(url)

            # FIXME: should have a more friendly error message
            assert not parsed_url.params and not parsed_url.query and not parsed_url.fragment

            # The port is a number, not a glob.
            if not parsed_url.hostname:
                raise ValueError("URL has no host: %r" % url)
            parsed_url.port # raises ValueError if the port isn't a number

            set.add(self, parsed_url)

        else:
            self.add('http://' + url)
            self.add('https://' + url)

    def __contains__(self, url):
        parsed_url = urllib.parse.urlparse(url)

        # FIXME: probably should tell user why...
        if parsed_url.params or parsed_url.query or parsed_url.fragment:
            return False

        # The port must be parseable, as otherwise the host and the port can't
        # be told apart.
        try:
            port = parsed_url.port
        except ValueError:
            return False

        for pattern in self:
            if (parsed_url.scheme == pattern.scheme and
                    parsed_url.path == pattern.path and
                    parsed_url.hostname is not None and
                    fnmatch.fnmatch(parsed_url.hostname, pattern.hostname) and
                    port == pattern.port):
                return True

        else:
            return False

    def __repr__(self):
       return 'UrlWhitelist([%s])' % ','.join("'%s'" % url.geturl() for url in self)

DEFAULT_CALENDAR_WHITELIST = \
    UrlWhitelist(['https://*.calendar.opentimestamps.org', # Run by Peter Todd
                  'https://*.calendar.eternitywall.com',   # Run by Riccardo Casatta
                  'https://*.calendar.catallaxy.com',      # Run by Bull Bitcoin
                 ])

DEFAULT_AGGREGATORS = \
    ('https://a.pool.opentimestamps.org',
     'https://b.pool.opentimestamps.org',
     'https://a.pool.eternitywall.com',
     'https://ots.btc.catallaxy.com')
