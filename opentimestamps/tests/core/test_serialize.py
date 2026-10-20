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

import unittest

from opentimestamps.core.serialize import *

class Test_serialization(unittest.TestCase):
    def test_assert_eof(self):
        """End-of-file assertions"""
        ctx = BytesDeserializationContext(b'')
        ctx.assert_eof()

        with self.assertRaises(TrailingGarbageError):
            ctx = BytesDeserializationContext(b'b')
            ctx.assert_eof()

    def test_varuint_length_limit(self):
        """Varuint encodings are limited in length"""
        ctx = BytesDeserializationContext(b'\xff' * 8 + b'\x7f')
        self.assertEqual(ctx.read_varuint(), 2**63 - 1)

        with self.assertRaises(DeserializationError):
            BytesDeserializationContext(b'\xff' * 9 + b'\x01').read_varuint()

        with self.assertRaises(DeserializationError):
            BytesDeserializationContext(b'\xff' * 2000 + b'\x01').read_varbytes(100)
