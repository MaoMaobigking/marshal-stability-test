# Python marshal Module Stability and Correctness Test Suite — Final Report

**Project**: marshal-stability-test
**Repository**: [MaoMaobigking/marshal-stability-test](https://github.com/MaoMaobigking/marshal-stability-test)
**Test Target**: Python standard library `marshal` module (Python 3.12)
**Testing Date**: June 11, 2026
**Environment**: Python 3.12.13, Windows, AMD64
**Team**: Chen Zhenye, Zhu Lipeng, Huang Shilei, You Hao, Yuan Shuai

---

## 1. Introduction

The `marshal` module implements serialization and deserialization of Python internal objects, primarily used for reading and writing .pyc pseudo-compiled bytecode. While designed to be architecture-independent, its format is intentionally unstable across Python major versions.

**Core research question**: Does the same Python input object always produce identical serialized marshal byte output? Here, "identical" means bit-identical (same hash), not merely logically equivalent.

## 2. Test Strategy

We applied a combination of black-box and white-box testing techniques to ensure comprehensive coverage.

### 2.1 Black-box Techniques

**Equivalence Partitioning (EP)**: Marshal-supported data types were partitioned into equivalence classes: scalar types (None, bool, int, float, complex, str, bytes, bytearray, Ellipsis, StopIteration) and collection types (list, tuple, dict, set, frozenset, code). Representative values from each class were selected for testing.

**Boundary Value Analysis (BVA)**: Systematic testing of type encoding system boundaries — integers at 2^7, 2^15, 2^31, 2^63 boundaries; floats at DBL_MIN, DBL_MAX, epsilon, and subnormal values; string lengths at the 255/256 boundary (TYPE_SHORT_ASCII vs TYPE_ASCII split); collection sizes from empty through large.

**Why EP and BVA were chosen**: These were natural fits because marshal"s behavior is primarily determined by input type (EP) and encoding format (BVA). A decision table approach was unnecessary since marshal does not have complex logical condition combinations.

**Fuzz Testing**: Random byte sequences fed to marshal.loads (200 iterations) to verify crash safety; random Python objects fed to marshal.dumps (100 iterations). Fuzz testing was chosen over orthogonal array testing because marshal.c deals with binary format parsing — fuzzing excels at discovering memory safety issues in such code.

**Error Guessing**: Constructed exceptional inputs based on knowledge of marshal format: truncated data, invalid type codes, oversized collections, and unsupported custom objects. This was used because marshal"s error-handling paths are best tested through boundary and spec-violation inputs.

### 2.2 White-box Techniques

**Type Coverage**: By reading CPython source (Python/marshal.c), we identified all TYPE_* constants and designed tests covering each type code path, from TYPE_NONE to TYPE_CODE. This was chosen because marshal"s core logic is a type-dispatch serialization engine.

**Data-flow Coverage (All-Defs/All-Uses)**: We designed tests targeting the FLAG_REF mechanism — when an object first appears in the reference table (definition point), it receives a type code with FLAG_REF bit; when the same object appears again (usage point), it receives a SHORT_REF reference. Shared-string and shared-list scenarios were constructed to exercise these paths. This was chosen because FLAG_REF is the key new mechanism in Python 3.12 marshal.

## 3. Test Suite Structure

The test suite comprises 81 test methods across 13 test classes.

| Test Class | Methods | Technique |
|---|---:|---|
| TestScalarTypes | 15 | EP + BVA |
| TestCollections | 14 | EP |
| TestCodeObjects | 4 | Type Coverage (white-box) |
| TestBoundaryValues | 7 | BVA |
| TestDeterminism | 5 | Determinism verification |
| TestRoundTrip | 13 | Round-trip correctness |
| TestRecursionAndNesting | 6 | Recursion/nesting |
| TestFuzz | 3 | Fuzz testing |
| TestWhiteBoxAllDefsAllUses | 3 | Data-flow (white-box) |
| TestErrorHandling | 5 | Error handling |
| TestCrossVersionAwareness | 2 | Version differences |
| TestFlagRefNonDeterminism | 3 | FLAG_REF analysis |
| TestCrossPlatform | 1 | Cross-platform stability |

**Results (Python 3.12.13 on Windows)**: 80 passed, 1 skipped, 0 failures.
The skipped test (test_cyclical_before_312) tests pre-3.12 behavior regarding cyclical references.

**PEP 8 Compliance**: The code has been verified against PEP 8 guidelines using `pycodestyle`.

## 4. Test Suite Completeness: Traceability Matrix

A complete traceability matrix mapping each test case to its requirements is provided as a separate Excel file (`traceability_matrix.xlsx`). Below is a condensed summary:

| Test Area | Test Classes | # Tests | Risk/Requirement Covered |
|---|---:|---:|---|
| Scalar Types | TestScalarTypes | 15 | None, bool, int, float, complex, str, bytes, Ellipsis, StopIteration |
| Collections | TestCollections | 14 | list, tuple, dict, set, frozenset (empty to large) |
| Code Objects | TestCodeObjects | 4 | .pyc bytecode serialization |
| Boundary Values | TestBoundaryValues | 7 | Integer/float/string/system boundaries |
| Determinism | TestDeterminism | 5 | Core research question: same input → same output |
| Round-trip | TestRoundTrip | 13 | dumps → loads correctness |
| Recursion | TestRecursionAndNesting | 6 | Deep nesting, wide structures, self-references |
| Fuzz | TestFuzz | 3 | Crash safety for random/malformed inputs |
| White-box | TestWhiteBoxAllDefsAllUses | 3 | Data-flow paths (All-Defs/All-Uses) |
| Errors | TestErrorHandling | 5 | Input validation and exception handling |
| Versions | TestCrossVersionAwareness | 2 | 3.11 vs 3.12 differences |
| FLAG_REF | TestFlagRefNonDeterminism | 3 | FLAG_REF non-determinism research |
| Cross-platform | TestCrossPlatform | 1 | Same Python version, same output |

## 5. Findings

### 5.1 Core Finding: FLAG_REF Non-Determinism

In Python 3.12+, marshal sets the FLAG_REF bit (0x80) for each object in the reference table. This causes an important non-determinism:

```python
>>> import marshal
>>> inf = float("inf")
>>> hex(marshal.dumps(inf)[0])
"0xe7"  # TYPE_FLOAT | FLAG_REF
>>> hex(marshal.dumps(float("inf"))[0])
"0x67"  # TYPE_FLOAT, no FLAG_REF
>>> marshal.dumps(inf) == marshal.dumps(float("inf"))
False  # Same value, different byte stream!
```

**Root cause**: marshal tracks object *identity* (memory pointer), not *value equality*. A value stored in a variable may be considered shareable by the compiler, thereby receiving the FLAG_REF type code. An inline expression always creates a new object and typically does not trigger the same reference-tracking behavior.

From a value semantics perspective, this is non-deterministic — the same logical value produces different byte streams. From an object identity perspective, it is deterministic — the same object pointer always produces the same output.

### 5.2 Additional Findings

- **Python 3.12 Type Code Restructuring**: All type codes changed in 3.12 (e.g., TYPE_TUPLE: 0x28 → 0xa9; TYPE_LIST: 0x5b → 0xdb; TYPE_DICT: 0x7b → 0xfb). The high bit (0x80) serves as FLAG_REF marker.
- **Recursive Structure Support**: Python 3.12+ natively supports self-referential lists and dictionaries. Earlier versions explicitly raised ValueError/OverflowError.
- **Shared Reference Preservation**: After marshal round-trip in 3.12+, shared references are preserved via the SHORT_REF mechanism: `loaded[0] is loaded[1]` returns True.

## 6. Limitations

1. **Limited cross-platform verification**: Testing was performed on Windows (Python 3.12.13) only. Ideal testing would include Linux and macOS.
2. **Limited fuzz depth**: Random byte testing primarily validates crash safety. A framework such as atheris or hypothesis would cover deeper parser state space.
3. **No extreme data volumes**: 2GB+ serialization scenarios were not tested due to time constraints.
4. **Incomplete code object coverage**: Not all code flag combinations (coroutines, async generators) were tested.
5. **Single byte order**: Tests ran on x86 (little-endian) only. Marshal"s architecture-independence claim remains unverified on big-endian architectures.

## 7. Conclusion

Through 81 systematic tests, we verified that Python 3.12"s marshal module performs well in:

- **Value-level determinism** (same process, same input → same output)
- **Round-trip correctness** (serialization → deserialization recovers original value)
- **Exception robustness** (graceful handling of invalid inputs)

The most significant finding is the FLAG_REF-introduced "object identity vs. value" non-determinism: the same value produces different serialized byte streams depending on object identity. While this behavior is reasonable in marshal"s design context (.pyc file generation), it constitutes a violation from a strict value-determinism standpoint.

**Report generated**: June 11, 2026
**Testing environment**: Python 3.12.13, Windows, AMD64
