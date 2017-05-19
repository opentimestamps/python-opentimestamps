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

import hashlib

from opentimestamps.core.op import UnaryOp, MsgValueError

@UnaryOp._register_op
class OpSecp256k1Commitment(UnaryOp):
    """Map (P || commit) -> [P + sha256(P||commit)G]_x for a given secp256k1 point P

    This is a unary op rather than a binary op to allow timestamps to also
    timestamp the point itself; in the event of an ECC break this might be
    relevant. Such a break would not affect the integrity of the commitment,
    but knowledge of the underlying key may be interesting in its own right.
    """
    TAG = b'\x09'
    TAG_NAME = 'secp256k1commitment'

    def _do_op_call(self, msg):
        if len(msg) < 33:
            raise MsgValueError("Missing secp256k1 point")

        pt = Point.decode(msg[0:33])

        hasher = hashlib.sha256()
        hasher.update(pt.encode())
        hasher.update(msg[33:])
        tweak = int.from_bytes(hasher.digest(), 'big')
        tweak_pt = SECP256K1_GEN.scalar_mul(tweak)
        final_pt = pt.add(tweak_pt)
        return final_pt.x.to_bytes(32, 'big')


## What follows is a lot of inefficient but explicit secp256k1 math
class Point(object):
    inf = True
    x = 0
    y = 0

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        if x == 0 and y == 0:
            self.inf = True
        else:
            self.inf = False

    def __repr__(self):
        if self.inf:
            return "Point(infinity)"
        else:
            return "Point(%x, %x)" % (self.x, self.y)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.inf == True and other.inf == True) or\
                   (self.inf == False and other.inf == False and self.x == other.x and self.y == other.y)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def decode(data):
        if len(data) != 33 or (data[0] != 2 and data[0] != 3):
            raise MsgValueError("Incorrectly formatted public key")

        x = int.from_bytes(data[1:], 'big')
        if x >= SECP256K1_P:
            raise MsgValueError("out of range x coordinate for secp256k1 point")

        ysqr = (x ** 3 + 7) % SECP256K1_P
        y = psqrt(ysqr)
        if pow(y, 2, SECP256K1_P) != ysqr:
            raise MsgValueError("invalid x coordinate for secp256k1 point")

        if y % 2 == 1 and data[0] == 2:
            y = SECP256K1_P - y
        if y % 2 == 0 and data[0] == 3:
            y = SECP256K1_P - y

        return Point(x, y)

    def encode(self):
        ret = bytearray(self.x.to_bytes(33, 'big'))
        assert(ret[0] == 0)
        if self.y % 2 == 1:
            ret[0] = 3
        else:
            ret[0] = 2
        return ret

    def add(self, pt):
        if self.inf:
            return pt
        if pt.inf:
            return self

        if self.x == pt.x:
            if self.y == SECP256K1_P - pt.y:
                return Point()
            else:
                assert(self.y == pt.y)
                lam = (3 * self.x ** 2 * pinv(2 * self.y)) % SECP256K1_P
        else:
            lam = ((pt.y - self.y) * pinv(pt.x - self.x)) % SECP256K1_P

        x3 = (lam ** 2 - self.x - pt.x) % SECP256K1_P
        y3 = (self.y + lam * (x3 - self.x)) % SECP256K1_P

        return Point(x3, SECP256K1_P - y3)

    def scalar_mul(self, s):
        ret = Point()
        add = self
        s = s % SECP256K1_N
        while s > 0:
            if s % 2 == 1:
                ret = ret.add(add)
            add = add.add(add)  # add
            s >>= 1
        return ret

SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
SECP256K1_GEN = Point(0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
                      0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)

def pinv(x):
    return pow(x, SECP256K1_P - 2, SECP256K1_P)

def psqrt(x):
    # using `>> 2` in place of `/ 4` keeps everything as an int rather than float
    return pow(x, (SECP256K1_P + 1) >> 2, SECP256K1_P)

