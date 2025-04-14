#!/usr/bin/env python3
"""
Test runner for the Growatt API project.
This script discovers and runs tests in the project.
"""

import unittest
import sys
import os
import argparse
from pathlib import Path

# Try to import coverage
try:
    import coverage # type: ignore
    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False


def run_tests(test_pattern=None, verbosity=1, run_coverage=False):
    """
    Run the tests.
    
    Args:
        test_pattern (str, optional): Pattern to match test files or methods.
        verbosity (int, optional): Verbosity level (1-3). Defaults to 1.
        run_coverage (bool, optional): Whether to run coverage. Defaults to False.
    
    Returns:
        bool: True if all tests passed, False otherwise.
    """
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Add the project root to Python path
    sys.path.insert(0, project_root)
    
    # Initialize coverage if requested
    cov = None
    if run_coverage and COVERAGE_AVAILABLE:
        cov = coverage.Coverage(
            source=[os.path.join(project_root, 'app')],
            omit=['*/__pycache__/*', '*/tests/*', '*/venv/*', '*/env/*']
        )
        cov.start()
    
    # Create test suite
    if test_pattern:
        # If a specific test pattern is provided
        if '.' in test_pattern:
            # Check if it's a specific test method (module.class.method)
            parts = test_pattern.split('.')
            if len(parts) >= 3:
                module_name, class_name, method_name = parts[:3]
                loader = unittest.TestLoader()
                test_module = __import__(module_name, fromlist=[class_name])
                test_class = getattr(test_module, class_name)
                tests = loader.loadTestsFromName(method_name, test_class)
            else:
                # Assume it's a class or module
                tests = unittest.defaultTestLoader.loadTestsFromName(test_pattern)
        else:
            # Assume it's a pattern for test files
            tests = unittest.defaultTestLoader.discover('tests', pattern=f'*{test_pattern}*.py')
    else:
        # Run all tests
        tests = unittest.defaultTestLoader.discover('tests')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(tests)
    
    # Generate coverage report if requested
    if run_coverage and COVERAGE_AVAILABLE and cov:
        cov.stop()
        cov.save()
        print("\nCoverage Report:")
        cov.report()
        # Generate HTML report
        html_dir = os.path.join(project_root, 'coverage_html')
        os.makedirs(html_dir, exist_ok=True)
        cov.html_report(directory=html_dir)
        print(f"\nHTML coverage report generated to: {html_dir}")
    
    return len(result.failures) == 0 and len(result.errors) == 0


def main():
    """Parse arguments and run tests."""
    parser = argparse.ArgumentParser(description='Run tests for the Growatt API project')
    
    parser.add_argument('-v', '--verbosity', type=int, default=1, choices=[1, 2, 3],
                        help='Test verbosity (1-3, default: 1)')
    parser.add_argument('-p', '--pattern', type=str, default=None,
                        help='Pattern to match test files or specific test (module.class.method)')
    parser.add_argument('-c', '--coverage', action='store_true',
                        help='Run with coverage report')
    
    args = parser.parse_args()
    
    if args.coverage and not COVERAGE_AVAILABLE:
        print("Coverage package is not installed. Run 'pip install coverage' to enable this feature.")
        args.coverage = False
    
    success = run_tests(
        test_pattern=args.pattern,
        verbosity=args.verbosity,
        run_coverage=args.coverage
    )
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

