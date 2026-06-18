# Python marshal Module Stability & Correctness Test Suite

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![PEP 8](https://img.shields.io/badge/code%20style-PEP%208-green)](https://www.python.org/dev/peps/pep-0008/)

A comprehensive test suite for Python"s internal `marshal` module, focusing on **bit-by-bit determinism** and **round-trip correctness**.

**Repository**: [MaoMaobigking/marshal-stability-test](https://github.com/MaoMaobigking/marshal-stability-test)

---

## Project Overview

The marshal module serializes/deserializes Python objects, primarily used for .pyc files. Core research question: **Does the same input always produce the same (serialized) output?**

This study answers this question through systematic testing covering OS differences, Python version variations, floating-point precision, recursive data structures, and collection size boundaries.

## Test Strategy

| Technique | Category | Description |
|---|---|---|
| **Equivalence Partitioning** | Black-box | All marshal-supported types: None, bool, int, float, complex, str, bytes, bytearray, list, tuple, dict, set, frozenset, code |
| **Boundary Value Analysis** | Black-box | Integer boundaries (2^31, 2^63), float boundaries (DBL_MIN, DBL_MAX, subnormal), string length boundaries (127, 255, 256, 65535, 65536), collection size boundaries |
| **Fuzz Testing** | Black-box | Random bytes to marshal.loads (200 rounds) + random objects to marshal.dumps (100 rounds) |
| **Error Guessing** | Black-box | Truncated data, invalid type codes, unsupported types, oversized data |
| **Type Coverage** | White-box | All TYPE_* constants in marshal.c |
| **Data-flow Coverage** | White-box | All-Defs: FLAG_REF/SHORT_REF paths; All-Uses: object sharing ref paths |
| **Round-trip Testing** | Correctness | marshal.dumps(obj) → marshal.loads(bytes) → value equivalence |
| **Recursion Testing** | Robustness | Deep nesting (50 levels), wide structures (10000 elements), self-referential lists/dicts (3.12+) |

## Test Results Summary

| Test Class | Methods | Technique |
|---|---:|---:|
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

**Result**: 80 passed, 1 skipped, 0 failures (Python 3.12.13, Windows, AMD64)

## Key Findings

### Core Finding: FLAG_REF Non-Determinism

In Python 3.12+, marshal sets the FLAG_REF bit (0x80) for each object in the reference table:

```python
import marshal
inf = float("inf")
marshal.dumps(inf)           # → 0xe7  (TYPE_FLOAT | FLAG_REF)
marshal.dumps(float("inf"))  # → 0x67  (TYPE_FLOAT, no FLAG_REF)
```

**Cause**: marshal tracks object *identity* (memory pointer), not *value equality*.

### Other Findings

- **Python 3.12 type code restructuring**: All type codes changed, supporting FLAG_REF
- **Recursive structure support**: 3.12+ natively supports self-referential structures
- **Shared reference preservation**: 3.12+ preserves shared references after round-trip

## Deliverables

| File | Description |
|---|---|
| `test_marshal.py` | Main test suite (81 tests, 13 classes) |
| `report.md` | Final report (English, ≤8 pages) |
| `traceability_matrix.xlsx` | Complete test case traceability matrix (80 test cases) |
| `mccabe_matrix.xlsx` | McCabe cyclomatic complexity matrix |
| `README.md` | This file |

## Requirements

- Python 3.8+ (recommended 3.12)
- No third-party dependencies (standard library unittest only)

## Running Tests

```bash
python -m unittest test_marshal.py -v
# or
python test_marshal.py
```

## License

MIT
