"""
Test Runner - Run all session tests

Executes unit tests and integration tests for the session management system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def run_tests():
    """Run all tests and report results."""
    print("\n" + "="*70)
    print("SESSION MANAGEMENT TEST SUITE")
    print("="*70)

    all_passed = True

    # Test 1: Unit tests
    print("\n" + "-"*70)
    print("RUNNING: Unit Tests (simple_mask_converter)")
    print("-"*70)
    try:
        from test_simple_converter import run_all_tests as run_unit_tests
        run_unit_tests()
        print("\n✓ Unit tests: PASSED")
    except Exception as e:
        print(f"\n✗ Unit tests: FAILED - {e}")
        all_passed = False

    # Test 2: Integration tests
    print("\n" + "-"*70)
    print("RUNNING: Integration Tests (production format)")
    print("-"*70)
    try:
        from test_production_format_fixes import test_production_format_integration
        test_production_format_integration()
        print("\n✓ Integration tests: PASSED")
    except Exception as e:
        print(f"\n✗ Integration tests: FAILED - {e}")
        all_passed = False

    # Final summary
    print("\n" + "="*70)
    if all_passed:
        print("TEST SUITE RESULT: ALL TESTS PASSED ✓")
    else:
        print("TEST SUITE RESULT: SOME TESTS FAILED ✗")
    print("="*70)

    return all_passed


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
