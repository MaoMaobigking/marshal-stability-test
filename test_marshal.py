"""

Marshal Stability and Correctness Test Suite



A comprehensive test suite for Python's marshal module, focusing on

strict bit-by-bit determinism (same input always produces identical

byte stream) and round-trip correctness.



Techniques applied:

  Black-box: Equivalence Partitioning, Boundary Value Analysis,

             Fuzz Testing, Error Guessing

  White-box: Type Coverage, Data-flow Coverage (All-Defs, All-Uses)



Compatible with Python 3.8+, fully tested on Python 3.12.

Adheres to PEP 8.

"""



import collections

import marshal

import os

import platform

import random

import struct

import sys

import types

import unittest



# ---------------------------------------------------------------------------

# Helper utilities

# ---------------------------------------------------------------------------



PY39 = sys.version_info >= (3, 9)

PY311 = sys.version_info >= (3, 11)

PY312 = sys.version_info >= (3, 12)





def _roundtrip(obj):

    """Serialize and deserialize, returning the recovered object."""

    data = marshal.dumps(obj)

    return marshal.loads(data)





def _dumps_self_consistent(obj, times=3):

    """Return True iff repeated dumps() of the same obj are identical."""

    ref = marshal.dumps(obj)

    for _ in range(times - 1):

        if marshal.dumps(obj) != ref:

            return False

    return True





# ---------------------------------------------------------------------------

# Test: Basic scalar types (equivalence partitioning)

# ---------------------------------------------------------------------------



class TestScalarTypes(unittest.TestCase):

    """Equivalence partitioning over marshal's supported scalar types."""



    def test_none(self):

        self.assertTrue(_dumps_self_consistent(None))

        self.assertIsNone(_roundtrip(None))



    def test_true(self):

        self.assertTrue(_dumps_self_consistent(True))

        self.assertIs(_roundtrip(True), True)



    def test_false(self):

        self.assertTrue(_dumps_self_consistent(False))

        self.assertIs(_roundtrip(False), False)



    def test_small_integer(self):

        for val in (0, 1, -1, 42, 127, -128):

            with self.subTest(val=val):

                self.assertTrue(_dumps_self_consistent(val))

                self.assertEqual(_roundtrip(val), val)



    def test_large_integer(self):

        vals = [2**15, -(2**15), 2**30, -(2**30), 2**31, -(2**31), 2**60, -(2**60), 2**63-1, -(2**63)]

        for val in vals:

            with self.subTest(val=val):

                self.assertTrue(_dumps_self_consistent(val))

                self.assertEqual(_roundtrip(val), val)



    def test_float_common(self):

        for val in (0.0, -0.0, 1.0, -1.5, 3.141592653589793):

            with self.subTest(val=val):

                self.assertTrue(_dumps_self_consistent(val))

                loaded = _roundtrip(val)

                self.assertEqual(loaded, val)



    def test_float_special_values(self):

        specials = [

            ("inf", float("inf")),

            ("-inf", float("-inf")),

            ("nan", float("nan")),

            ("-0.0", -0.0),

            ("0.0", 0.0),

        ]

        for label, val in specials:

            with self.subTest(label=label):

                self.assertTrue(_dumps_self_consistent(val))

                loaded = _roundtrip(val)

                self.assertEqual(struct.pack("d", loaded), struct.pack("d", val))

        self.assertNotEqual(marshal.dumps(0.0), marshal.dumps(-0.0))

        self.assertEqual(marshal.dumps(float("nan")), marshal.dumps(float("nan")))



    def test_complex(self):

        for val in (1+2j, 0j, -1.5+3j, complex("inf"), complex("nan")):

            with self.subTest(val=str(val)):

                self.assertTrue(_dumps_self_consistent(val))

                loaded_val = _roundtrip(val)
                # Use struct comparison for NaN safety (NaN != NaN)
                self.assertEqual(struct.pack("d", loaded_val.real), struct.pack("d", val.real))
                self.assertEqual(struct.pack("d", loaded_val.imag), struct.pack("d", val.imag))



    def test_short_ascii_string(self):

        strings = ["", "a", "hello", "a" * 127, "a" * 255]

        for s in strings:

            with self.subTest(s=s[:20]):

                self.assertTrue(_dumps_self_consistent(s))

                self.assertEqual(_roundtrip(s), s)



    def test_long_ascii_string(self):

        s = "x" * 65536

        self.assertTrue(_dumps_self_consistent(s))

        self.assertEqual(_roundtrip(s), s)



    def test_unicode_string(self):

        s = "\u00e9\u2202\U0001f600"

        self.assertTrue(_dumps_self_consistent(s))

        self.assertEqual(_roundtrip(s), s)



    def test_bytes(self):

        for b in (b"", bytes([0]), b"hello", b"\xff" * 255, bytes([0]) * 65536):

            with self.subTest(b=str(b[:20])):

                self.assertTrue(_dumps_self_consistent(b))

                self.assertEqual(_roundtrip(b), b)



    def test_bytearray(self):

        ba = bytearray(b"test_data")

        self.assertTrue(_dumps_self_consistent(ba))

        loaded = _roundtrip(ba)

        self.assertIsInstance(loaded, bytes)

        self.assertEqual(loaded, bytes(ba))



    def test_ellipsis(self):

        self.assertTrue(_dumps_self_consistent(...))

        self.assertIs(_roundtrip(...), ...)



    def test_stopiteration(self):

        self.assertTrue(_dumps_self_consistent(StopIteration))

        loaded = _roundtrip(StopIteration)

        self.assertIs(type(loaded), type(StopIteration))





# ---------------------------------------------------------------------------

# Test: Collection types (equivalence partitioning + boundary value)

# ---------------------------------------------------------------------------



class TestCollections(unittest.TestCase):

    """Equivalence classes for list, tuple, dict, set, frozenset."""



    def test_empty_list(self):

        self.assertTrue(_dumps_self_consistent([]))

        self.assertEqual(_roundtrip([]), [])



    def test_small_list(self):

        lst = [1, "two", 3.0]

        self.assertTrue(_dumps_self_consistent(lst))

        self.assertEqual(_roundtrip(lst), lst)



    def test_large_list(self):

        lst = list(range(1000))

        self.assertTrue(_dumps_self_consistent(lst))

        self.assertEqual(_roundtrip(lst), lst)



    def test_empty_tuple(self):

        self.assertTrue(_dumps_self_consistent(()))

        self.assertEqual(_roundtrip(()), ())



    def test_small_tuple(self):

        tup = (42, "hello", None)

        self.assertTrue(_dumps_self_consistent(tup))

        self.assertEqual(_roundtrip(tup), tup)



    def test_nested_tuple(self):

        tup = (1, (2, (3, (4,))))

        self.assertTrue(_dumps_self_consistent(tup))

        self.assertEqual(_roundtrip(tup), tup)



    def test_empty_dict(self):

        self.assertTrue(_dumps_self_consistent({}))

        self.assertEqual(_roundtrip({}), {})



    def test_small_dict(self):

        d = {"key": "value", "num": 42}

        self.assertTrue(_dumps_self_consistent(d))

        self.assertEqual(_roundtrip(d), d)



    def test_dict_numeric_keys(self):

        d = {1: "one", 2: "two", 3: "three"}

        self.assertTrue(_dumps_self_consistent(d))

        self.assertEqual(_roundtrip(d), d)



    def test_dict_mixed_keys(self):

        d = {1: "int", "str": 2, (3,): [4]}

        self.assertTrue(_dumps_self_consistent(d))

        loaded = _roundtrip(d)

        self.assertEqual(loaded, d)



    def test_dict_large(self):

        d = {str(i): i for i in range(100)}

        self.assertTrue(_dumps_self_consistent(d))

        self.assertEqual(_roundtrip(d), d)



    def test_empty_set(self):

        self.assertTrue(_dumps_self_consistent(set()))

        self.assertEqual(_roundtrip(set()), set())



    def test_small_set(self):

        s = {1, 2, 3}

        self.assertTrue(_dumps_self_consistent(s))

        self.assertEqual(_roundtrip(s), s)



    def test_empty_frozenset(self):

        self.assertTrue(_dumps_self_consistent(frozenset()))

        loaded = _roundtrip(frozenset())

        self.assertIsInstance(loaded, frozenset)

        self.assertEqual(loaded, frozenset())



    def test_small_frozenset(self):

        fs = frozenset({1, "a", 3.0})

        self.assertTrue(_dumps_self_consistent(fs))

        self.assertEqual(_roundtrip(fs), fs)





# ---------------------------------------------------------------------------

# Test: Code objects (white-box: essential for .pyc files)

# ---------------------------------------------------------------------------



class TestCodeObjects(unittest.TestCase):

    """White-box: code objects are the primary use case for marshal (.pyc)."""



    SAMPLE = "def foo(x): return x + 1\nresult = foo(42)\n"



    def test_code_determinism(self):

        code = compile(self.SAMPLE, "<test>", "exec")

        self.assertTrue(_dumps_self_consistent(code))



    def test_code_roundtrip(self):

        code = compile(self.SAMPLE, "<test>", "exec")

        loaded = _roundtrip(code)

        self.assertIsInstance(loaded, types.CodeType)



    def test_lambda_code(self):

        code = compile("lambda x: x * 2", "<test>", "eval")

        self.assertTrue(_dumps_self_consistent(code))

        loaded = _roundtrip(code)

        self.assertIsInstance(loaded, types.CodeType)



    def test_code_with_constants(self):

        code = compile("x = [1, 2, 3]; y = {chr(65): 1}", "<test>", "exec")

        self.assertTrue(_dumps_self_consistent(code))

        loaded = _roundtrip(code)

        self.assertIsInstance(loaded, types.CodeType)





# ---------------------------------------------------------------------------

# Test: Boundary value analysis

# ---------------------------------------------------------------------------



class TestBoundaryValues(unittest.TestCase):

    """Systematic boundary-value analysis across marshal type space."""



    def test_int_boundaries(self):

        boundaries = [0, 1, -1, 2**7-1, -(2**7), 2**15-1, -(2**15),

                      2**31-1, -(2**31), 2**31, -(2**31)-1, 2**63-1, -(2**63)]

        for val in boundaries:

            with self.subTest(val=val):

                self.assertTrue(_dumps_self_consistent(val))

                self.assertEqual(_roundtrip(val), val)



    def test_int_sys_maxsize(self):

        self.assertTrue(_dumps_self_consistent(sys.maxsize))

        self.assertEqual(_roundtrip(sys.maxsize), sys.maxsize)



    def test_float_boundaries(self):

        vals = [sys.float_info.min, sys.float_info.max, sys.float_info.epsilon]

        for val in vals:

            with self.subTest(val=val):

                self.assertTrue(_dumps_self_consistent(val))

                self.assertEqual(_roundtrip(val), val)



    def test_float_subnormal(self):

        val = sys.float_info.min * (1 + sys.float_info.epsilon) / (2**52)

        self.assertTrue(_dumps_self_consistent(val))

        loaded = _roundtrip(val)

        self.assertEqual(struct.pack("d", loaded), struct.pack("d", val))



    def test_string_length_boundaries(self):

        for n in [0, 1, 127, 254, 255, 256, 65535, 65536]:

            s = "a" * n

            with self.subTest(n=n):

                self.assertTrue(_dumps_self_consistent(s))

                self.assertEqual(_roundtrip(s), s)



    def test_bytes_length_boundaries(self):

        for n in [0, 1, 127, 254, 255, 256, 65535, 65536]:

            b = b"\\xff" * n

            with self.subTest(n=n):

                self.assertTrue(_dumps_self_consistent(b))

                self.assertEqual(_roundtrip(b), b)



    def test_collection_size_boundaries(self):

        for size in [0, 1, 2, 3, 100, 1000]:

            with self.subTest(size=size, type="list"):

                self.assertTrue(_dumps_self_consistent(list(range(size))))

                self.assertEqual(_roundtrip(list(range(size))), list(range(size)))

            with self.subTest(size=size, type="tuple"):

                self.assertTrue(_dumps_self_consistent(tuple(range(size))))

                self.assertEqual(_roundtrip(tuple(range(size))), tuple(range(size)))





# ---------------------------------------------------------------------------

# Test: Determinism (the core research question)

# ---------------------------------------------------------------------------



class TestDeterminism(unittest.TestCase):

    """Verify identical inputs always produce identical byte streams."""



    def test_primitive_determinism(self):

        for obj in [None, True, False, 42, 0, -1, 2**60, 3.14,

                    float("inf"), float("nan"), -0.0, 1+2j, "", "hello",

                    b"", b"data", set(), frozenset()]:

            with self.subTest(obj=repr(obj)[:40]):

                self.assertTrue(_dumps_self_consistent(obj))



    def test_collection_determinism(self):

        for obj in [[], [1,2,3], (), (1,"two"), {}, {"a":1},

                     set(), {1,2,3}, frozenset(), frozenset({1,2}),

                     [{"nested": (1,2,[3])}]]:

            with self.subTest(obj=repr(obj)[:60]):

                self.assertTrue(_dumps_self_consistent(obj))



    def test_independent_calls_determinism(self):

        self.assertEqual(marshal.dumps(list(range(100))),

                         marshal.dumps(list(range(100))))

        c = {"key_" + str(i): i for i in range(50)}

        d = {"key_" + str(i): i for i in range(50)}

        self.assertEqual(marshal.dumps(c), marshal.dumps(d))



    def test_shared_string_determinism(self):

        s = "shared_string_42"

        # Each tuple must be self-consistent
        self.assertTrue(_dumps_self_consistent((s, s)))
        self.assertTrue(_dumps_self_consistent(("shared_string_42", "shared_string_42")))


        self.assertTrue(_dumps_self_consistent((s, s)))



    def test_shared_list_determinism(self):

        inner = [1, 2, 3]

        self.assertTrue(_dumps_self_consistent([inner, inner]))





# ---------------------------------------------------------------------------

# Test: Round-trip correctness

# ---------------------------------------------------------------------------



class TestRoundTrip(unittest.TestCase):

    """Verify marshal.loads(marshal.dumps(obj)) recovers original value."""



    def test_roundtrip_none(self):

        self.assertIsNone(_roundtrip(None))



    def test_roundtrip_bool(self):

        self.assertIs(_roundtrip(True), True)

        self.assertIs(_roundtrip(False), False)



    def test_roundtrip_int(self):

        for val in (0, 1, -1, 2**31, 2**63-1, sys.maxsize):

            self.assertEqual(_roundtrip(val), val)



    def test_roundtrip_float(self):

        for val in (0.0, 3.14, -1.5, sys.float_info.max, sys.float_info.min):

            self.assertEqual(_roundtrip(val), val)



    def test_roundtrip_complex(self):

        for val in (0j, 1+2j, 3.14-1.5j):

            self.assertEqual(_roundtrip(val), val)



    def test_roundtrip_str(self):

        for s in ("", "hello", "a" * 1000):

            self.assertEqual(_roundtrip(s), s)



    def test_roundtrip_bytes(self):

        for b in (b"", bytes([0]), b"\xff" * 1000):

            self.assertEqual(_roundtrip(b), b)



    def test_roundtrip_list(self):

        for lst in ([], [1], [1, "two", 3.0], list(range(500))):

            self.assertEqual(_roundtrip(lst), lst)



    def test_roundtrip_tuple(self):

        for tup in ((), (1,), (1, "two", 3.0), tuple(range(500))):

            self.assertEqual(_roundtrip(tup), tup)



    def test_roundtrip_dict(self):

        for d in ({}, {"a": 1}, {1: "one", "two": 2},

                  {str(i): i for i in range(50)}):

            self.assertEqual(_roundtrip(d), d)



    def test_roundtrip_set(self):

        for s in (set(), {1}, {1, "a", 3.0}):

            self.assertEqual(_roundtrip(s), s)



    def test_roundtrip_frozenset(self):

        for fs in (frozenset(), frozenset({1, "a"})):

            loaded = _roundtrip(fs)

            self.assertIsInstance(loaded, frozenset)

            self.assertEqual(loaded, fs)





# ---------------------------------------------------------------------------

# Test: Recursion and nesting

# ---------------------------------------------------------------------------



class TestRecursionAndNesting(unittest.TestCase):

    """Verify behavior around deep nesting and cyclical references."""



    def test_deeply_nested_tuple(self):

        depth = min(50, sys.getrecursionlimit() // 10)

        t = ()

        for _ in range(depth):

            t = (t,)

        self.assertTrue(_dumps_self_consistent(t))

        self.assertEqual(_roundtrip(t), t)



    def test_deeply_nested_list(self):

        depth = min(50, sys.getrecursionlimit() // 10)

        lst = []

        for _ in range(depth):

            lst = [lst]

        self.assertTrue(_dumps_self_consistent(lst))



    def test_wide_nesting(self):

        t = tuple(range(10000))

        self.assertTrue(_dumps_self_consistent(t))

        self.assertEqual(len(_roundtrip(t)), 10000)



    @unittest.skipIf(not PY312, "Recursive marshal support added in 3.12")

    def test_self_referential_list(self):

        lst = []

        lst.append(lst)

        self.assertTrue(_dumps_self_consistent(lst))

        loaded = _roundtrip(lst)

        self.assertIsInstance(loaded, list)

        self.assertEqual(len(loaded), 1)

        self.assertIs(loaded[0], loaded)



    @unittest.skipIf(not PY312, "Recursive marshal support added in 3.12")

    def test_self_referential_dict(self):

        d = {}

        d["self"] = d

        self.assertTrue(_dumps_self_consistent(d))

        loaded = _roundtrip(d)

        self.assertIsInstance(loaded, dict)

        self.assertIs(loaded["self"], loaded)



    @unittest.skipIf(PY312, "Pre-3.12 raises on cyclical references")

    def test_cyclical_before_312(self):

        lst = []

        lst.append(lst)

        with self.assertRaises((ValueError, OverflowError)):

            marshal.dumps(lst)





# ---------------------------------------------------------------------------

# Test: Fuzz testing

# ---------------------------------------------------------------------------



class TestFuzz(unittest.TestCase):

    """Fuzz marshal.loads with random bytes and dumps with random objects."""



    ITER_LOADS = 200

    ITER_DUMPS = 100



    def test_fuzz_loads_random(self):

        rng = random.Random(42)

        for _ in range(self.ITER_LOADS):

            data = bytes(rng.randint(0, 255) for _ in range(rng.randint(1, 128)))

            try:

                marshal.loads(data)

            except Exception:

                pass



    def test_fuzz_loads_malformed(self):

        rng = random.Random(7)

        for _ in range(self.ITER_LOADS // 2):

            data = bytes(rng.randint(1, 255) for _ in range(rng.randint(4, 64)))

            try:

                marshal.loads(data)

            except Exception:

                pass



    def test_fuzz_dumps_random(self):

        rng = random.Random(1)

        for _ in range(self.ITER_DUMPS):

            try:

                marshal.dumps(self._rand_obj(rng, 0))

            except Exception:

                pass



    @staticmethod

    def _rand_obj(rng, depth):

        if depth > 3:

            return rng.choice([None, True, False, 0, "", b"", []])

        kind = rng.randint(0, 10)

        if kind == 0: return None

        if kind == 1: return True

        if kind == 2: return False

        if kind == 3: return rng.randint(-(2**30), 2**30)

        if kind == 4: return rng.random() * 1e6

        if kind == 5:

            return "".join(chr(rng.randint(32, 126)) for _ in range(rng.randint(0, 64)))

        if kind == 6:

            return bytes(rng.randint(0, 255) for _ in range(rng.randint(0, 32)))

        if kind == 7:

            return [TestFuzz._rand_obj(rng, depth+1) for _ in range(rng.randint(0, 10))]

        if kind == 8:

            return tuple(TestFuzz._rand_obj(rng, depth+1) for _ in range(rng.randint(0, 10)))

        if kind == 9:

            keys = [str(i) for i in range(rng.randint(0, 5))]

            return {k: TestFuzz._rand_obj(rng, depth+1) for k in keys}

        return float("inf")





# ---------------------------------------------------------------------------

# Test: White-box data-flow coverage

# ---------------------------------------------------------------------------



class TestWhiteBoxAllDefsAllUses(unittest.TestCase):

    """White-box: target specific marshal.c data-flow paths."""



    def test_short_ascii_interned_path(self):

        s = "interned_hello"

        container = (s, s, s)

        self.assertTrue(_dumps_self_consistent(container))

        loaded = _roundtrip(container)

        self.assertEqual(loaded, ("interned_hello",) * 3)



    def test_flag_ref_positive(self):

        lst = [1, 2, 3]

        data = marshal.dumps(lst)

        if PY312:

            self.assertEqual(data[0], 0xdb)

        else:

            self.assertEqual(data[0], 0x5b)



    def test_reused_shared_list(self):

        shared = [1, 2, 3]

        outer = [shared, shared]

        data = marshal.dumps(outer)

        loaded = marshal.loads(data)

        self.assertEqual(loaded, [[1, 2, 3], [1, 2, 3]])

        if PY312:

            self.assertIs(loaded[0], loaded[1])





# ---------------------------------------------------------------------------

# Test: Error / exception handling

# ---------------------------------------------------------------------------



class TestErrorHandling(unittest.TestCase):

    """Verify marshal raises well-defined exceptions for invalid inputs."""



    def test_loads_empty(self):

        with self.assertRaises(EOFError):

            marshal.loads(b"")



    def test_loads_truncated(self):

        data = marshal.dumps([1, 2, 3])

        for length in range(1, len(data)):

            with self.subTest(length=length):

                with self.assertRaises((EOFError, ValueError)):

                    marshal.loads(data[:length])



    def test_loads_invalid_type(self):

        with self.assertRaises(ValueError):

            marshal.loads(bytes([0]))



    def test_unsupported_types(self):

        with self.assertRaises((TypeError, ValueError)):

            marshal.dumps(object())

        with self.assertRaises((TypeError, ValueError)):

            marshal.dumps(lambda x: x)



    def test_oversized_load(self):

        bad = b"\xdb\xff\xff\xff\x7f"

        with self.assertRaises((ValueError, MemoryError, OverflowError, EOFError)):

            marshal.loads(bad)





# ---------------------------------------------------------------------------

# Test: Cross-version awareness

# ---------------------------------------------------------------------------



class TestCrossVersionAwareness(unittest.TestCase):

    """Document version-dependent behavior. marshal is NOT cross-version stable."""



    def test_type_code_format_changed_in_312(self):

        data = marshal.dumps((1, 2, 3))

        if PY312:

            self.assertEqual(data[0], 0xa9)

        else:

            self.assertEqual(data[0], 0x28)



    def test_recursive_support_changed_in_312(self):

        lst = []

        lst.append(lst)

        if PY312:

            dump = marshal.dumps(lst)

            self.assertGreater(len(dump), 0)

        else:

            with self.assertRaises((ValueError, OverflowError)):

                marshal.dumps(lst)





# ---------------------------------------------------------------------------

# Test: FLAG_REF non-determinism analysis (research finding)

# ---------------------------------------------------------------------------



class TestFlagRefNonDeterminism(unittest.TestCase):

    """Investigate FLAG_REF-based non-determinism found during research.



    In Python 3.12, when the same *value* (e.g. float('inf')) is stored

    in a variable before marshal.dumps(), it receives the FLAG_REF type

    code (0xe7). When passed inline, it does NOT (0x67). This means the

    same logical input produces different byte output based on object

    identity tracking -- a violation of value-based determinism.

    """



    def test_inf_variable_vs_inline(self):

        inf_var = float("inf")

        dump_var = marshal.dumps(inf_var)

        dump_literal = marshal.dumps(float("inf"))

        if PY312:

            self.assertEqual(dump_var[0], 0xe7)

            self.assertEqual(dump_literal[0], 0x67)

            self.assertNotEqual(dump_var, dump_literal)



    def test_nan_variable_vs_inline(self):

        nan_var = float("nan")

        if PY312:

            self.assertEqual(marshal.dumps(nan_var)[0], 0xe7)

            self.assertEqual(marshal.dumps(float("nan"))[0], 0x67)



    def test_regular_float_not_affected(self):

        self.assertEqual(marshal.dumps(3.14), marshal.dumps(3.14))





# ---------------------------------------------------------------------------

# Test: Cross-platform stability

# ---------------------------------------------------------------------------



class TestCrossPlatform(unittest.TestCase):

    """Verify same Python version produces same output within process."""



    def test_same_version_same_output(self):

        for obj in [None, True, 42, 3.14, "hello", (1,2,3), [1,2,3], {"key":"value"}]:

            with self.subTest(obj=repr(obj)):

                self.assertEqual(marshal.dumps(obj), marshal.dumps(obj))

                self.assertEqual(marshal.dumps(obj), marshal.dumps(obj))





# ---------------------------------------------------------------------------

# Entry point

# ---------------------------------------------------------------------------



if __name__ == "__main__":

    unittest.main(verbosity=2)

