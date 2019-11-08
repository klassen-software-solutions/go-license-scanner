#!/usr/bin/env python3

"""Script to scan Go modules for license requirements."""

import argparse
import logging
import os
import sys

import DependancyScanner
from LicenseScanner import Scanner
from Reporter import Reporter

def main():
    """Main entry point."""

    parser = argparse.ArgumentParser()
    parser.add_argument('--json', action='store_true',
                        help='Generate a JSON license report on the standard output device')
    parser.add_argument('--pdf',
                        help='Generate a PDF license report in the given file')
    parser.add_argument('--verbose', action='store_true', help='Show debugging information')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARN)
    directory = os.getcwd()
    dependancies = DependancyScanner.scan(directory)

    scanner = Scanner(dependancies)
    scanner.scan()
    scanner.print_new_licenses()

    if args.json:
        reporter = Reporter(scanner)
        reporter.json_report()
    elif args.pdf and len(args.pdf) > 0:
        reporter = Reporter(scanner)
        reporter.pdf_report(args.pdf, os.path.basename(directory))
    else:
        bad_count = scanner.count_invalid_licenses()
        if bad_count > 0:
            sys.exit(bad_count)

if __name__ == '__main__':
    main()
