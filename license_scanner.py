#!/usr/bin/env python3

"""Script to scan Go modules for license requirements."""

import argparse
import logging
import os
import sys

import DependancyScanner
import Reporter
from LicenseScanner import Scanner

def main():
    """Main entry point."""

    parser = argparse.ArgumentParser()
    parser.add_argument('--report', action='store_true', help='Generate a license report')
    parser.add_argument('--verbose', action='store_true', help='Show debugging information')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)
    dependancies = DependancyScanner.scan(os.getcwd())

    scanner = Scanner(dependancies)
    scanner.scan()

    if args.report:
        Reporter.report(scanner)
    else:
        bad_count = scanner.count_invalid_licenses()
        if bad_count > 0:
            sys.exit(bad_count)

if __name__ == '__main__':
    main()
