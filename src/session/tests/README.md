# Session Management Tests

Comprehensive test suite for the session management system and production format fixes.

## Test Organization

```
src/session/tests/
├── __init__.py                           # Package initialization
├── README.md                             # This file
├── run_all_tests.py                      # Test runner (runs all tests)
├── test_simple_converter.py              # Unit tests for converter
├── test_production_format_fixes.py       # Integration tests
└── TEST_RESULTS.md                       # Detailed test results
```

## Running Tests

### Run All Tests

Run the complete test suite from the project root:

```bash
python src/session/tests/run_all_tests.py
```

**Expected output:**
```
TEST SUITE RESULT: ALL TESTS PASSED ✓
```

### Run Individual Tests

**Unit tests only:**
```bash
python src/session/tests/test_simple_converter.py
```

**Integration tests only:**
```bash
python src/session/tests/test_production_format_fixes.py
```

## Test Coverage

### Unit Tests (`test_simple_converter.py`)

Tests individual converter functions in isolation:

1. **extract_sparse_points()** - Extract points from mask arrays
2. **convert_mask_to_json()** - Convert PNG masks to JSON
3. **json_to_mask()** - Convert JSON to PNG masks
4. **Round-trip conversion** - mask → JSON → mask preservation
5. **validate_annotation_format()** - Format validation
6. **count_annotation_points()** - Point counting

**Coverage:** 6 tests

### Integration Tests (`test_production_format_fixes.py`)

Tests complete workflow with real data:

1. **Configuration loading** - Load dataset and training configs
2. **Session creation** - Create session with 1754 masks
3. **get_available_iterations()** - Test SessionManager method
4. **Format validation** - Verify production format
5. **Point counting** - Test annotation counting
6. **Round-trip conversion** - Test 1754 files
7. **Data preservation** - Verify accuracy
8. **Config extraction** - Test ignore_index from config
9. **Format compliance** - Exact VIZ_SOFTWARE format match

**Coverage:** 9 tests

## Test Results

**Current Status:** ✅ ALL TESTS PASSED (15/15)

See [TEST_RESULTS.md](TEST_RESULTS.md) for detailed results.

### Key Metrics

| Metric | Value |
|--------|-------|
| Unit tests | 6/6 ✅ |
| Integration tests | 9/9 ✅ |
| Masks converted | 1754/1754 ✅ |
| Conversion failures | 0 ✅ |
| Round-trip accuracy | 100% ✅ |

## What's Being Tested

### Production Format

The tests verify that the system uses the exact format from VIZ_SOFTWARE production:

```json
{
  "format_version": "1.0",
  "image": {
    "name": "0.png",
    "width": 512,
    "height": 512
  },
  "annotations": [
    [124, 48, 0],
    [388, 182, 3],
    [207, 249, 1]
  ],
  "iteration": 0,
  "created_at": "2025-09-24T17:30:01.894508Z"
}
```

### Fixed Issues

All tests verify fixes for these issues:

1. ✅ Mask conversion failures (1754 failures → 0)
2. ✅ AttributeError: get_available_iterations()
3. ✅ ignore_index hardcoding (now from config)
4. ✅ Format mismatches (unified format)
5. ✅ Round-trip accuracy (100% preservation)

## Requirements

Tests use only standard project dependencies:
- numpy
- Pillow (PIL)
- Standard library (json, pathlib, tempfile)

No additional test frameworks required.

## Test Data

Tests use:
- **Real data:** VAIHINGEN sparse masks (1754 files)
- **Synthetic data:** Generated test masks
- **Temporary directories:** All test files cleaned up automatically

## Troubleshooting

### Tests fail with "configs not found"

**Solution:** Run tests from project root, not from tests directory.

```bash
# Correct
cd /mnt/d/SIAL
python src/session/tests/run_all_tests.py

# Incorrect
cd /mnt/d/SIAL/src/session/tests
python run_all_tests.py
```

### Import errors

**Solution:** Ensure project root is in Python path. Tests handle this automatically.

## Adding New Tests

To add new tests:

1. Create test file in `src/session/tests/`
2. Name it `test_*.py`
3. Add to `run_all_tests.py` if needed
4. Run test suite to verify

Example:

```python
def test_new_feature():
    """Test description."""
    # Test code here
    assert result == expected
    print("✓ Test passed")
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```bash
# Exit code 0 if all pass, 1 if any fail
python src/session/tests/run_all_tests.py
```

## Documentation

- [TEST_RESULTS.md](TEST_RESULTS.md) - Detailed test results and metrics
- [../simple_mask_converter.py](../simple_mask_converter.py) - Production converter implementation
- [../mask_utils.py](../mask_utils.py) - Updated mask utilities

## Support

For issues with tests:
1. Check [TEST_RESULTS.md](TEST_RESULTS.md) for expected behavior
2. Verify running from project root
3. Check that VAIHINGEN data is available at `VAIHINGEN/sparse_masks/`
