# Copyright (C) 2026 The OpenTimestamps developers
#
# This file is part of python-opentimestamps.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-opentimestamps including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.

"""Property tests for deserialization

Deserializing arbitrary bytes either succeeds or raises DeserializationError,
and what is accepted serializes to bytes that deserialize to an equal object.
"""

import unittest
import warnings

try:
    from hypothesis import given, settings, strategies as st
except ImportError:
    raise unittest.SkipTest('hypothesis is not installed')

from opentimestamps.core.serialize import *
from opentimestamps.core.timestamp import *

ATTESTATION_TAGS = [bytes.fromhex(h) for h in (
    '83dfe30d2ef90c8e', '0588960d73d71901', '06869a0d73d71b45', '30fe8087b5c7ead7')]
UNARY_OP_TAGS = [b'\x02', b'\x03', b'\x08', b'\x67', b'\xf2', b'\xf3']
BINARY_OP_TAGS = [b'\xf0', b'\xf1']
URI_CHARS = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._/:"


def varuint(n):
    ctx = BytesSerializationContext()
    ctx.write_varuint(n)
    return ctx.getbytes()


def varbytes(b):
    return varuint(len(b)) + b


heights = st.one_of(st.integers(0, 2**32 + 5), st.integers(0, 2**70))
uris = st.lists(st.sampled_from(URI_CHARS), max_size=40).map(bytes)
garbage = st.binary(max_size=8)


@st.composite
def attestations(draw):
    tag = draw(st.one_of(st.sampled_from(ATTESTATION_TAGS), st.binary(min_size=8, max_size=8)))
    if tag == ATTESTATION_TAGS[0]:
        payload = varbytes(draw(st.one_of(uris, st.binary(max_size=40))))
    elif tag in ATTESTATION_TAGS:
        payload = varuint(draw(heights))
    else:
        payload = draw(st.binary(max_size=40))
    if draw(st.booleans()):
        payload += draw(garbage)
    payload_len = len(payload)
    if draw(st.integers(0, 19)) == 0:
        payload_len = draw(st.integers(0, 9000))
    return b'\x00' + tag + varuint(payload_len) + payload


@st.composite
def ops(draw):
    kind = draw(st.integers(0, 9))
    if kind < 6:
        return draw(st.sampled_from(UNARY_OP_TAGS))
    if kind < 9:
        arg = draw(st.one_of(st.binary(min_size=1, max_size=40), st.binary(max_size=4200)))
        return draw(st.sampled_from(BINARY_OP_TAGS)) + varbytes(arg)
    return draw(st.binary(min_size=1, max_size=3))


def nodes(children):
    item = st.one_of(attestations(), st.tuples(ops(), children).map(lambda t: t[0] + t[1]))
    return st.lists(item, min_size=1, max_size=4).map(
        lambda items: b''.join(b'\xff' + i for i in items[:-1]) + items[-1])


timestamps = st.recursive(attestations(), nodes, max_leaves=30)
msgs = st.one_of(st.binary(min_size=20, max_size=32), st.binary(max_size=200),
                 st.binary(min_size=2040, max_size=2060))
file_hash_ops = st.sampled_from([(b'\x08', 32), (b'\x02', 20), (b'\x03', 20), (b'\x67', 32), (b'\x00', 0)])

property_settings = settings(max_examples=200, deadline=None, database=None)


def serialize(obj):
    ctx = BytesSerializationContext()
    obj.serialize(ctx)
    return ctx.getbytes()


def deserialize_timestamp(msg, data):
    ctx = BytesDeserializationContext(data)
    stamp = Timestamp.deserialize(ctx, msg)
    ctx.assert_eof()
    return stamp


def deserialize_detached(data):
    return DetachedTimestampFile.deserialize(BytesDeserializationContext(data))


class Test_DeserializeProperties(unittest.TestCase):
    def check_round_trip(self, deserialize, data):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', PendingDeprecationWarning)  # OpReverse
            try:
                obj = deserialize(data)
            except DeserializationError:
                return
            out = serialize(obj)
            obj2 = deserialize(out)
        self.assertEqual(obj2, obj)
        self.assertEqual(serialize(obj2), out)

    @property_settings
    @given(st.binary(max_size=64), st.binary(max_size=2000))
    def test_raw_timestamp(self, msg, data):
        """Timestamp from random bytes"""
        self.check_round_trip(lambda b: deserialize_timestamp(msg, b), data)

    @property_settings
    @given(st.binary(max_size=200))
    def test_raw_detached(self, data):
        """Detached timestamp file from random bytes after the magic"""
        self.check_round_trip(deserialize_detached, DetachedTimestampFile.HEADER_MAGIC + data)

    @property_settings
    @given(msgs, timestamps, st.one_of(st.just(b''), garbage))
    def test_grammar_timestamp(self, msg, data, tail):
        """Timestamp from generated ops and attestations"""
        self.check_round_trip(lambda b: deserialize_timestamp(msg, b), data + tail)

    @property_settings
    @given(file_hash_ops, st.data(), timestamps)
    def test_grammar_detached(self, file_hash_op, data, body):
        """Detached timestamp file from generated ops and attestations"""
        tag, digest_len = file_hash_op
        digest = data.draw(st.binary(min_size=digest_len, max_size=digest_len))
        self.check_round_trip(deserialize_detached,
                              DetachedTimestampFile.HEADER_MAGIC + b'\x01' + tag + digest + body)
