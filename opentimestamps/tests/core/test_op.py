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

import hashlib
import io
import unittest
import unittest.mock

from opentimestamps.core.op import *

class Test_Op(unittest.TestCase):
    def test_append(self):
        """Append operation"""
        self.assertEqual(OpAppend(b'suffix')(b'msg'), b'msgsuffix')

    def test_append_invalid_arg(self):
        """Append op, invalid argument"""
        with self.assertRaises(TypeError):
            OpAppend('')
        with self.assertRaises(OpArgValueError):
            OpAppend(b'')
        with self.assertRaises(OpArgValueError):
            OpAppend(b'.'*4097)

    def test_append_invalid_msg(self):
        """Append op, invalid message"""
        with self.assertRaises(TypeError):
            OpAppend(b'.')(None)
        with self.assertRaises(TypeError):
            OpAppend(b'.')('')

        OpAppend(b'.')(b'.'*4095)
        with self.assertRaises(MsgValueError):
            OpAppend(b'.')(b'.'*4096)

    def test_prepend(self):
        """Prepend operation"""
        self.assertEqual(OpPrepend(b'prefix')(b'msg'), b'prefixmsg')

    def test_prepend_invalid_arg(self):
        """Prepend op, invalid argument"""
        with self.assertRaises(TypeError):
            OpPrepend('')
        with self.assertRaises(OpArgValueError):
            OpPrepend(b'')
        with self.assertRaises(OpArgValueError):
            OpPrepend(b'.'*4097)

    def test_prepend_invalid_msg(self):
        """Prepend op, invalid message"""
        with self.assertRaises(TypeError):
            OpPrepend(b'.')(None)
        with self.assertRaises(TypeError):
            OpPrepend(b'.')('')

        OpPrepend(b'.')(b'.'*4095)
        with self.assertRaises(MsgValueError):
            OpPrepend(b'.')(b'.'*4096)

#    def test_reverse(self):
#        """Reverse operation"""
#        self.assertEqual(OpReverse()(b'abcd'), b'dcba')

    def test_hexlify(self):
        """Hexlify operation"""
        for msg, expected in ((b'\x00', b'00'),
                              (b'\xde\xad\xbe\xef', b'deadbeef')):
            self.assertEqual(OpHexlify()(msg), expected)

    def test_hexlify_msg_length_limits(self):
        """Hexlify message length limits"""
        OpHexlify()(b'.'*2048)
        with self.assertRaises(MsgValueError):
            OpHexlify()(b'.'*2049)
        with self.assertRaises(MsgValueError):
            OpHexlify()(b'')

    def test_sha256(self):
        """SHA256 operation"""
        self.assertEqual(OpSHA256()(b''), bytes.fromhex('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'))

    def test_ripemd160(self):
        """RIPEMD160 operation"""
        self.assertEqual(OpRIPEMD160()(b''), bytes.fromhex('9c1185a5c5e9fc54612808977ee8f548b2258d31'))

    def test_ripemd160_vectors(self):
        """RIPEMD160 test vectors, with and without hashlib's ripemd160"""
        # See https://homes.esat.kuleuven.be/~bosselae/ripemd160.html
        vectors = [
            (b"", "9c1185a5c5e9fc54612808977ee8f548b2258d31"),
            (b"a", "0bdc9d2d256b3ee9daae347be6f4dc835a467ffe"),
            (b"abc", "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc"),
            (b"message digest", "5d0689ef49d2fae572b881b123a85ffa21595f36"),
            (b"abcdefghijklmnopqrstuvwxyz",
                "f71c27109c692c1b56bbdceb5b9d2865b3708dbc"),
            (b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
                "12a053384a9c0c88e405a06c27dcf49ada62eb2b"),
            (b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
                "b0e20b6e3116640286ed3a87a5713079b21f5189"),
            (b"1234567890" * 8, "9b752e45573d4b39f4dbd3323cab82bf63326bfb"),
            (b"a" * 1000000, "52783243c1697bdbe16d37f97f68f08325dc1528"),
        ]

        hashlib_new = hashlib.new
        def new_without_ripemd160(name, *args, **kwargs):
            if name == 'ripemd160':
                raise ValueError('unsupported hash type ' + name)
            return hashlib_new(name, *args, **kwargs)

        for new in (hashlib_new, new_without_ripemd160):
            with unittest.mock.patch('hashlib.new', new):
                for msg, hexout in vectors:
                    expected = bytes.fromhex(hexout)
                    if len(msg) <= OpRIPEMD160.MAX_MSG_LENGTH:
                        self.assertEqual(OpRIPEMD160()(msg), expected)
                    self.assertEqual(OpRIPEMD160().hash_fd(io.BytesIO(msg)), expected)

    def test_equality(self):
        """Operation equality"""
        self.assertEqual(OpReverse(), OpReverse())
        self.assertNotEqual(OpReverse(), OpSHA1())

        self.assertEqual(OpAppend(b'foo'), OpAppend(b'foo'))
        self.assertNotEqual(OpAppend(b'foo'), OpAppend(b'bar'))
        self.assertNotEqual(OpAppend(b'foo'), OpPrepend(b'foo'))

    def test_ordering(self):
        """Operation ordering"""
        self.assertTrue(OpSHA1() < OpRIPEMD160())
        # FIXME: more tests

    def test_keccak256(self):
        """KECCAK256 operation"""
        self.assertEqual(OpKECCAK256()(b''), bytes.fromhex('c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'))
        self.assertEqual(OpKECCAK256()(b'\x80'), bytes.fromhex('56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421'))
