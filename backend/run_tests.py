#!/usr/bin/env python3
"""
Test runner script for HB-Staffing backend
"""

import sys
import os
import subprocess
import coverage

def run_tests():
    """Run all backend tests with coverage"""
    print("🧪 Running HB-Staffing Backend Tests")
    print("=" * 50)

    # Change to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    # Run tests with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "--cov=.",
        "--cov-report=html",
        "--cov-report=term-missing",
        "tests/",
        "-v"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # Print test summary
        print("\n" + "=" * 50)
        if result.returncode == 0:
            print("✅ All tests passed!")
            print("📊 Coverage report generated in htmlcov/index.html")
        else:
            print("❌ Some tests failed!")
            return False

    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

    return True

def run_specific_test(test_path):
    """Run a specific test"""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    cmd = [sys.executable, "-m", "pytest", test_path, "-v"]
    result = subprocess.run(cmd)

    return result.returncode == 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_path = sys.argv[1]
        success = run_specific_test(test_path)
    else:
        # Run all tests
        success = run_tests()

    sys.exit(0 if success else 1)
