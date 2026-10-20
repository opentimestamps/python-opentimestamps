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

from opentimestamps.core.notary import *
from opentimestamps.core.serialize import *
from opentimestamps.core.timestamp import *
from opentimestamps.core.op import *

class Test_Timestamp(unittest.TestCase):
    def test_add_op(self):
        """Adding operations to timestamps"""
        t = Timestamp(b'abcd')
        t.ops.add(OpAppend(b'efgh'))
        self.assertEqual(t.ops[OpAppend(b'efgh')], Timestamp(b'abcdefgh'))

        # The second add should succeed with the timestamp unchanged
        t.ops.add(OpAppend(b'efgh'))
        self.assertEqual(t.ops[OpAppend(b'efgh')], Timestamp(b'abcdefgh'))

    def test_set_result_timestamp(self):
        """Setting an op result timestamp"""
        t1 = Timestamp(b'foo')
        t2 = t1.ops.add(OpAppend(b'bar'))
        t3 = t2.ops.add(OpAppend(b'baz'))

        self.assertEqual(t1.ops[OpAppend(b'bar')].ops[OpAppend(b'baz')].msg, b'foobarbaz')

        t1.ops[OpAppend(b'bar')] = Timestamp(b'foobar')

        self.assertTrue(OpAppend(b'baz') not in t1.ops[OpAppend(b'bar')].ops)

    def test_set_fail_if_wrong_message(self):
        """Setting an op result timestamp fails if the messages don't match"""
        t = Timestamp(b'abcd')
        t.ops.add(OpSHA256())

        with self.assertRaises(ValueError):
            t.ops[OpSHA256()] = Timestamp(b'wrong')

    def test_merge(self):
        """Merging timestamps"""
        with self.assertRaises(ValueError):
            Timestamp(b'a').merge(Timestamp(b'b'))

        t1 = Timestamp(b'a')
        t2 = Timestamp(b'a')
        t2.attestations.add(PendingAttestation('foobar'))

        t1.merge(t2)
        self.assertEqual(t1, t2)

        # FIXME: more tests

    def test_serialization(self):
        """Timestamp serialization/deserialization"""
        def T(expected_instance, expected_serialized):
            ctx = BytesSerializationContext()
            expected_instance.serialize(ctx)
            actual_serialized = ctx.getbytes()

            self.assertEqual(expected_serialized, actual_serialized)

            actual_instance = Timestamp.deserialize(BytesDeserializationContext(expected_serialized), expected_instance.msg)
            self.assertEqual(expected_instance, actual_instance)


        stamp = Timestamp(b'foo')
        stamp.attestations.add(PendingAttestation('foobar'))

        T(stamp, b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobar')

        stamp.attestations.add(PendingAttestation('barfoo'))
        T(stamp, b'\xff' + (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'barfoo') + \
                 (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobar'))


        stamp.attestations.add(PendingAttestation('foobaz'))
        T(stamp, b'\xff' + (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'barfoo') + \
                 b'\xff' + (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobar') + \
                 (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobaz'))

        sha256_stamp = stamp.ops.add(OpSHA256())

        # Should fail - empty timestamps can't be serialized
        with self.assertRaises(ValueError):
            ctx = BytesSerializationContext()
            stamp.serialize(ctx)

        sha256_stamp.attestations.add(PendingAttestation('deeper'))
        T(stamp, b'\xff' + (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'barfoo') + \
                 b'\xff' + (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobar') + \
                 b'\xff' + (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobaz') + \
                 b'\x08' + (b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'deeper'))

    def test_deserialization_invalid_op_msg(self):
        """Timestamp deserialization when message is invalid for op"""
        serialized = (b'\xf0\x01\x00' + # OpAppend(b'\x00')
                      b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'barfoo') # perfectly valid pending attestation

        # Perfectly ok, results is 4096 bytes long
        Timestamp.deserialize(BytesDeserializationContext(serialized), b'.'*4095)

        with self.assertRaises(DeserializationError):
            # Not ok, result would be 4097 bytes long
            Timestamp.deserialize(BytesDeserializationContext(serialized), b'.'*4096)

    def test_deserialization_invalid_op_msg_2(self):
        """Deserialization of a timestamp that exceeds the recursion limit"""
        serialized = (b'\x08'*256 + # OpSHA256, 256 times
                      b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'barfoo') # perfectly valid pending attestation

        with self.assertRaises(RecursionLimitError):
            Timestamp.deserialize(BytesDeserializationContext(serialized), b'')

    def test_deserialization_memory_limit(self):
        """Deserialization fails if the op results use too much memory"""
        def serialize(branches):
            # Each branch is an append op that yields a result of 4096 bytes
            ctx = BytesSerializationContext()
            t = Timestamp(b'\x00' * 4000)
            for i in range(branches):
                t.ops.add(OpAppend(bytes(96 - 2) + i.to_bytes(2, 'big'))).attestations.add(PendingAttestation(''))
            t.serialize(ctx)
            return ctx.getbytes()

        branches_under_limit = Timestamp.MAX_MEMORY_USAGE // (4096 + Timestamp.NODE_MEMORY_USAGE)

        ctx = BytesDeserializationContext(serialize(branches_under_limit))
        Timestamp.deserialize(ctx, b'\x00' * 4000)

        ctx = BytesDeserializationContext(serialize(branches_under_limit + 1))
        with self.assertRaises(DeserializationError):
            Timestamp.deserialize(ctx, b'\x00' * 4000)

    def test_deserialization_many_small_results(self):
        """Deserialization fails if there are too many op results"""
        t = Timestamp(b'')
        for i in range(Timestamp.MAX_MEMORY_USAGE // Timestamp.NODE_MEMORY_USAGE + 1):
            t.ops.add(OpAppend(i.to_bytes(3, 'big'))).attestations.add(PendingAttestation(''))
        ctx = BytesSerializationContext()
        t.serialize(ctx)

        with self.assertRaises(DeserializationError):
            Timestamp.deserialize(BytesDeserializationContext(ctx.getbytes()), b'')

    def test_merge_memory_limit(self):
        """Merging fails, changing nothing, past the memory limit"""
        def stamp(indexes):
            # Each branch is an append op that yields a result of 4096 bytes
            t = Timestamp(b'\x00' * 4000)
            for i in indexes:
                t.ops.add(OpAppend(bytes(96 - 2) + i.to_bytes(2, 'big'))).attestations.add(PendingAttestation(''))
            return t

        def serialized(t):
            ctx = BytesSerializationContext()
            t.serialize(ctx)
            return ctx.getbytes()

        branches_under_limit = Timestamp.MAX_MEMORY_USAGE // (4096 + Timestamp.NODE_MEMORY_USAGE)
        half = branches_under_limit // 2

        # Two halves that make up exactly the limit merge, and the result
        # reads back
        t = stamp(range(half))
        t.merge(stamp(range(half, branches_under_limit)))
        self.assertEqual(len(t.ops), branches_under_limit)
        Timestamp.deserialize(BytesDeserializationContext(serialized(t)), b'\x00' * 4000)

        # One more branch is refused, and the timestamp is left as it was
        before = serialized(t)
        with self.assertRaises(ValueError):
            t.merge(stamp([branches_under_limit]))
        self.assertEqual(serialized(t), before)

        # Several branches, some of them new, are refused as a whole
        with self.assertRaises(ValueError):
            t.merge(stamp(range(half, branches_under_limit + 1)))
        self.assertEqual(serialized(t), before)

        # What it has already is not an addition, nor is an attestation
        other = stamp(range(half))
        other.attestations.add(PendingAttestation('foobar'))
        t.merge(other)
        self.assertIn(PendingAttestation('foobar'), t.attestations)
        self.assertEqual(len(t.ops), branches_under_limit)

    def test_merge_memory_limit_deep_branch(self):
        """A merge that adds a deep branch past the limit is refused"""
        t1 = Timestamp(b'')
        t1.ops.add(OpAppend(b'a')).attestations.add(PendingAttestation(''))
        t2 = Timestamp(b'')
        node = t2.ops.add(OpAppend(b'a'))
        for i in range(Timestamp.MAX_MEMORY_USAGE // Timestamp.NODE_MEMORY_USAGE):
            node.ops.add(OpAppend(i.to_bytes(3, 'big'))).attestations.add(PendingAttestation(''))

        with self.assertRaises(ValueError):
            t1.merge(t2)
        self.assertEqual(len(t1.ops[OpAppend(b'a')].ops), 0)

    def test_merge_memory_limit_below_a_root(self):
        """The limit of a merge below the root is checked against the root"""
        def build():
            # A node below the root, as a pending attestation sits below the
            # nonce and the digest of a stamp
            root = Timestamp(b'')
            node = root.ops.add(OpAppend(b'a')).ops.add(OpSHA256())
            node.attestations.add(PendingAttestation(''))
            return root, node

        def response(msg, branches):
            t = Timestamp(msg)
            for i in range(branches):
                t.ops.add(OpAppend(i.to_bytes(3, 'big'))).attestations.add(PendingAttestation(''))
            return t

        def serialized(t):
            ctx = BytesSerializationContext()
            t.serialize(ctx)
            return ctx.getbytes()

        root, node = build()
        # The node alone stays under the limit, the root goes over it by the
        # two op results above the node
        branches = Timestamp.MAX_MEMORY_USAGE // (Timestamp.NODE_MEMORY_USAGE + len(node.msg) + 3)
        other = response(node.msg, branches)
        self.assertLessEqual(node._memory_usage() + other._memory_usage(), Timestamp.MAX_MEMORY_USAGE)
        self.assertGreater(root._memory_usage() + other._memory_usage(), Timestamp.MAX_MEMORY_USAGE)

        before = serialized(root)
        with self.assertRaises(ValueError):
            node.merge(other, root=root)
        self.assertEqual(serialized(root), before)

        with self.assertRaises(TypeError):
            node.merge(other, root=b'')

        # Without the root the merge passes, which is why callers pass it
        node.merge(other)
        with self.assertRaises(DeserializationError):
            Timestamp.deserialize(BytesDeserializationContext(serialized(root)), b'')

        # A merge that fits under the root is done
        root, node = build()
        node.merge(response(node.msg, 10), root=root)
        self.assertEqual(len(node.ops), 10)

    def test_str_tree(self):
        """Converting timestamp to tree"""
        t = Timestamp(b'')
        t.ops.add(OpAppend(b'\x01'))
        t.ops.add(OpSHA256())
        self.assertEqual(t.str_tree(), " -> sha256\n -> append 01\n")

    def test_equality(self):
        """Checking timestamp equality"""
        t1 = Timestamp(b'')
        t1.attestations = {BitcoinBlockHeaderAttestation(1), PendingAttestation("")}
        t2 = Timestamp(b'')
        self.assertFalse(t1 == t2)
        t2.attestations = {PendingAttestation(""), BitcoinBlockHeaderAttestation(1)}
        self.assertTrue(t1 == t2)

class Test_DetachedTimestampFile(unittest.TestCase):
    def test_create_from_file(self):
        file_stamp = DetachedTimestampFile.from_fd(OpSHA256(), io.BytesIO(b''))
        self.assertEqual(file_stamp.file_digest, bytes.fromhex('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'))

    def test_hash_fd(self):
        file_stamp = DetachedTimestampFile.from_fd(OpSHA256(), io.BytesIO(b''))

        result = file_stamp.file_hash_op.hash_fd(io.BytesIO(b''))
        self.assertEqual(result, bytes.fromhex('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'))

    def test_serialization(self):
        def T(expected_instance, expected_serialized):
            ctx = BytesSerializationContext()
            expected_instance.serialize(ctx)
            actual_serialized = ctx.getbytes()

            self.assertEqual(expected_serialized, actual_serialized)

            actual_instance = DetachedTimestampFile.deserialize(BytesDeserializationContext(expected_serialized))
            self.assertEqual(expected_instance, actual_instance)

        file_stamp = DetachedTimestampFile.from_fd(OpSHA256(), io.BytesIO(b''))
        file_stamp.timestamp.attestations.add(PendingAttestation('foobar'))

        T(file_stamp, (b'\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94' +
                       b'\x01' + # major version
                       b'\x08' + bytes.fromhex('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855') +
                       b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobar'))

    def test_deserialization_failures(self):
        """Deserialization failures"""

        for serialized, expected_error in ((b'', BadMagicError),
                                           (b'\x00Not a OpenTimestamps Proof \x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94\x01', BadMagicError),
                                           (b'\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94\x00', UnsupportedMajorVersion),
                                           (b'\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94\x01' +
                                            b'\x42' + # Not a valid opcode
                                            b'\x00'*32 +
                                            b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobar', DeserializationError),
                                           (b'\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94\x01' +
                                             b'\x08' + bytes.fromhex('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855') +
                                             b'\x00' + bytes.fromhex('83dfe30d2ef90c8e' + '07' + '06') + b'foobar' +
                                             b'trailing garbage', TrailingGarbageError)):

            with self.assertRaises(expected_error):
                ctx = BytesDeserializationContext(serialized)
                DetachedTimestampFile.deserialize(ctx)

    def test_keccak256_is_not_a_file_hash_op(self):
        """Keccak256 can't be the file hash op of a detached timestamp"""
        ctx = BytesDeserializationContext(DetachedTimestampFile.HEADER_MAGIC + b'\x01' + OpKECCAK256.TAG + bytes(32) + b'\x00' + PendingAttestation.TAG + b'\x01\x00')
        with self.assertRaises(DeserializationError):
            DetachedTimestampFile.deserialize(ctx)

        # but it remains valid within a timestamp
        t = Timestamp(b'')
        t.ops.add(OpKECCAK256()).attestations.add(PendingAttestation(''))
        ctx = BytesSerializationContext()
        t.serialize(ctx)
        self.assertEqual(Timestamp.deserialize(BytesDeserializationContext(ctx.getbytes()), b''), t)


class Test_cat_sha256(unittest.TestCase):
    def test(self):
        left = Timestamp(b'foo')
        right = Timestamp(b'bar')

        stamp_left_right= cat_sha256(left, right)
        self.assertEqual(stamp_left_right.msg, bytes.fromhex('c3ab8ff13720e8ad9047dd39466b3c8974e592c2fa383d4a3960714caef0c4f2'))

        righter = Timestamp(b'baz')
        stamp_righter = cat_sha256(stamp_left_right, righter)
        self.assertEqual(stamp_righter.msg, bytes.fromhex('23388b16c66f1fa37ef14af8eb081712d570813e2afb8c8ae86efa726f3b7276'))


class Test_make_merkle_tree(unittest.TestCase):
    def test(self):
        def T(n, expected_merkle_root):
            roots = [Timestamp(bytes([i])) for i in range(n)]
            tip = make_merkle_tree(roots)

            self.assertEqual(tip.msg, expected_merkle_root)

            for root in roots:
                pass # FIXME: check all roots lead to same timestamp

        # Returned unchanged!
        T(1, bytes.fromhex('00'))

        # Manually calculated w/ pen-and-paper
        T(2, bytes.fromhex('b413f47d13ee2fe6c845b2ee141af81de858df4ec549a58b7970bb96645bc8d2'))
        T(3, bytes.fromhex('e6aa639123d8aac95d13d365ec3779dade4b49c083a8fed97d7bfc0d89bb6a5e'))
        T(4, bytes.fromhex('7699a4fdd6b8b6908a344f73b8f05c8e1400f7253f544602c442ff5c65504b24'))
        T(5, bytes.fromhex('aaa9609d0c949fee22c1c941a4432f32dc1c2de939e4af25207f0dc62df0dbd8'))
        T(6, bytes.fromhex('ebdb4245f648b7e77b60f4f8a99a6d0529d1d372f98f35478b3284f16da93c06'))
        T(7, bytes.fromhex('ba4603a311279dea32e8958bfb660c86237157bf79e6bfee857803e811d91b8f'))
