# Copyright (C) 2017 The OpenTimestamps developers
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
import unittest

from opentimestamps.core.secp256k1 import *

class Test_Secp256k1(unittest.TestCase):
    def test_point_rt(self):
        """Point encoding round trip"""
        gen = SECP256K1_GEN
        encode = gen.encode()
        self.assertEqual(encode, binascii.unhexlify("0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"))
        gen2 = Point().decode(encode)
        self.assertEqual(gen, gen2)

    def test_pinv(self):
        """Field inversion mod p"""
        self.assertEqual(pinv(1), 1)
        self.assertEqual(pinv(2), 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffff7ffffe18)
        self.assertEqual(pinv(3), 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa9fffffd75)
        self.assertEqual(2, pinv(0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffff7ffffe18))
        self.assertEqual(3, pinv(0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa9fffffd75))

    def test_psqrt(self):
        """Field square root mod p"""
        self.assertEqual(psqrt(1), 1)
        self.assertEqual(psqrt(2), 0x210c790573632359b1edb4302c117d8a132654692c3feeb7de3a86ac3f3b53f7)
        self.assertEqual(psqrt(4), 2)
        # may return the sqrt or its negative
        self.assertEqual(psqrt(9), SECP256K1_P - 3)
        self.assertEqual(psqrt(49), SECP256K1_P - 7)

    def test_point_add(self):
        """Point adding and doubling"""

        inf = Point()
        # P random chosen by dice roll
        p1 = Point(0x394867ad93f5c9612e8d8b7600443334026e648e365337d799190e845d649e67,
                   0x0b84af9a00c1a55a7ac03917e59b21c68d1ffdf18720c3ad279077049cfaaf63)
        # 2P
        p2 = Point(0x8e6575f6c759aea04a8ec65f61f71eba237a0af54292d41e3a4bac2efa922dea,
                   0x2b3c07687787ff07ae312305f30481c451ae3b78d4f479a3b729615fedc040e4)
        # -2P
        np2 = Point(0x8e6575f6c759aea04a8ec65f61f71eba237a0af54292d41e3a4bac2efa922dea,
                    0xd4c3f897887800f851cedcfa0cfb7e3bae51c4872b0b865c48d69e9f123fbb4b)
        # 3P
        p3 = Point(0x53dd5e495c7404790f9347470cc9c38ee239809c758f02ec04ba641ab3d0e043,
                   0xd7a4f5e5bdf21000b1fe7216adbea92cb9917d8fea7b37628c1eddb409a5cd3f)

        self.assertEqual(inf.add(inf), inf)
        self.assertEqual(p1.add(inf), p1)
        self.assertEqual(inf.add(p1), p1)
        self.assertEqual(p1.add(p1), p2)
        self.assertEqual(p1.add(p2), p3)
        self.assertEqual(p2.add(p1), p3)
        self.assertEqual(p3.add(np2), p1)
        self.assertEqual(np2.add(p3), p1)
        self.assertEqual(p2.add(np2), inf)
        self.assertEqual(np2.add(p2), inf)

    def test_scalar_mul(self):
        inf = Point()
        # P random chosen by dice roll
        p1 = Point(0x394867ad93f5c9612e8d8b7600443334026e648e365337d799190e845d649e67,
                   0x0b84af9a00c1a55a7ac03917e59b21c68d1ffdf18720c3ad279077049cfaaf63)
        # 2P
        p2 = Point(0x8e6575f6c759aea04a8ec65f61f71eba237a0af54292d41e3a4bac2efa922dea,
                   0x2b3c07687787ff07ae312305f30481c451ae3b78d4f479a3b729615fedc040e4)
        # -2P
        np2 = Point(0x8e6575f6c759aea04a8ec65f61f71eba237a0af54292d41e3a4bac2efa922dea,
                    0xd4c3f897887800f851cedcfa0cfb7e3bae51c4872b0b865c48d69e9f123fbb4b)
        # 3P
        p3 = Point(0x53dd5e495c7404790f9347470cc9c38ee239809c758f02ec04ba641ab3d0e043,
                   0xd7a4f5e5bdf21000b1fe7216adbea92cb9917d8fea7b37628c1eddb409a5cd3f)

        # nP
        n = 0xa91ce154dcab9adabe08cc1ee84ec3cd0f426bbc08a54a1c41bd25f2587caedd
        pn = Point(0x9dc4b057a857ad2ef3535b4a207a7bfc9264e8fcacf718c895db7ead8d445b26,
                   0x5af110ecb68636e5c352b69fc6348173932b83ca64587a91fd88af1446e33979)

        self.assertEqual(inf.scalar_mul(0), inf)
        self.assertEqual(inf.scalar_mul(1000), inf)
        self.assertEqual(inf.scalar_mul(-1), inf)

        self.assertEqual(p1.scalar_mul(0), inf)
        self.assertEqual(p1.scalar_mul(1), p1)
        self.assertEqual(p1.scalar_mul(2), p2)
        self.assertEqual(p1.scalar_mul(-2), np2)
        self.assertEqual(p2.scalar_mul(-1), np2)
        self.assertEqual(p1.scalar_mul(3), p3)

