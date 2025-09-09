#!/usr/bin/env python3
"""
Test runner script for YouTube Analytics application

This script provides convenient commands to run different types of tests:
- Unit tests
- Integration tests
- Coverage reports
- Specific test modules

Usage:
    python run_tests.py [options]
    
Examples:
    python run_tests.py --unit                    # Run only unit tests
    python run_tests.py --integration             # Run only integration tests
    python run_tests.py --coverage                # Run tests with coverage
    python run_tests.py --module auth             # Run tests for auth module
    python run_tests.py --fast                    # Run fast tests only
    python run_tests.py --all                     # Run all tests
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and handle errors."""
    if description:
        print(f"\n{description}")
        print("=" * len(description))
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        return False
    except FileNotFoundError:
        print(f"Error: Command not found: {cmd[0]}")
        print("Make sure pytest is installed: pip install pytest")
        return False

def check_dependencies():
    """Check if required testing dependencies are installed."""
    required_packages = [
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'pytest-asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("Missing required testing packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Test runner for YouTube Analytics application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --unit                    Run only unit tests
  %(prog)s --integration             Run only integration tests
  %(prog)s --coverage                Run tests with coverage report
  %(prog)s --module auth             Run tests for specific module
  %(prog)s --fast                    Run fast tests only (exclude slow tests)
  %(prog)s --all                     Run all tests
  %(prog)s --verbose                 Run with verbose output
  %(prog)s --parallel                Run tests in parallel
        """
    )
    
    # Test selection options
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument(
        '--unit', 
        action='store_true',
        help='Run only unit tests'
    )
    test_group.add_argument(
        '--integration', 
        action='store_true',
        help='Run only integration tests'
    )
    test_group.add_argument(
        '--all', 
        action='store_true',
        help='Run all tests (default)'
    )
    
    # Module-specific testing
    parser.add_argument(
        '--module', 
        choices=['auth', 'database', 'ingestion', 'gemini', 'ui', 'optimization'],
        help='Run tests for specific module'
    )
    
    # Test execution options
    parser.add_argument(
        '--fast', 
        action='store_true',
        help='Run fast tests only (exclude slow tests)'
    )
    parser.add_argument(
        '--coverage', 
        action='store_true',
        help='Run tests with coverage report'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Run with verbose output'
    )
    parser.add_argument(
        '--parallel', 
        action='store_true',
        help='Run tests in parallel'
    )
    parser.add_argument(
        '--html-report', 
        action='store_true',
        help='Generate HTML coverage report'
    )
    parser.add_argument(
        '--xml-report', 
        action='store_true',
        help='Generate XML coverage report'
    )
    
    # Output options
    parser.add_argument(
        '--quiet', 
        action='store_true',
        help='Minimal output'
    )
    parser.add_argument(
        '--tb', 
        choices=['short', 'long', 'auto', 'line', 'native', 'no'],
        default='short',
        help='Traceback print mode'
    )
    
    # Additional pytest arguments
    parser.add_argument(
        '--pytest-args', 
        nargs='*',
        help='Additional arguments to pass to pytest'
    )
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path('tests').exists():
        print("Error: tests directory not found.")
        print("Make sure you're running this script from the project root directory.")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add test selection
    if args.unit:
        cmd.extend(['-m', 'unit'])
    elif args.integration:
        cmd.extend(['-m', 'integration'])
    elif args.module:
        cmd.append(f'tests/test_{args.module}.py')
    else:
        # Run all tests by default
        cmd.append('tests/')
    
    # Add execution options
    if args.fast:
        cmd.extend(['-m', 'not slow'])
    
    if args.verbose:
        cmd.append('-v')
    elif args.quiet:
        cmd.append('-q')
    
    if args.parallel:
        cmd.extend(['-n', 'auto'])
    
    # Add traceback option
    cmd.extend(['--tb', args.tb])
    
    # Add coverage options
    if args.coverage or args.html_report or args.xml_report:
        cmd.extend(['--cov=src', '--cov-report=term-missing'])
        
        if args.html_report:
            cmd.extend(['--cov-report=html:htmlcov'])
        
        if args.xml_report:
            cmd.extend(['--cov-report=xml'])
    
    # Add any additional pytest arguments
    if args.pytest_args:
        cmd.extend(args.pytest_args)
    
    # Run the tests
    success = run_command(cmd, "Running tests")
    
    if success:
        print("\n✅ All tests passed!")
        
        if args.coverage or args.html_report:
            print("\n📊 Coverage report generated:")
            if args.html_report:
                html_report = Path('htmlcov/index.html')
                if html_report.exists():
                    print(f"  HTML: {html_report.absolute()}")
            if args.xml_report:
                xml_report = Path('coverage.xml')
                if xml_report.exists():
                    print(f"  XML: {xml_report.absolute()}")
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)

def run_specific_test_suites():
    """Run specific test suites for CI/CD."""
    test_suites = {
        'unit': {
            'description': 'Unit Tests',
            'command': ['python', '-m', 'pytest', 'tests/', '-m', 'unit', '-v']
        },
        'integration': {
            'description': 'Integration Tests',
            'command': ['python', '-m', 'pytest', 'tests/', '-m', 'integration', '-v']
        },
        'coverage': {
            'description': 'Coverage Report',
            'command': [
                'python', '-m', 'pytest', 'tests/', 
                '--cov=src', '--cov-report=html', '--cov-report=xml', 
                '--cov-report=term-missing', '--cov-fail-under=80'
            ]
        }
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in test_suites:
        suite_name = sys.argv[1]
        suite = test_suites[suite_name]
        
        success = run_command(suite['command'], suite['description'])
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    # Check if this is being called for specific test suites
    if len(sys.argv) > 1 and sys.argv[1] in ['unit', 'integration', 'coverage']:
        run_specific_test_suites()
    else:
        main()