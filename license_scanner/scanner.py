
"""License scanner entry point
"""

import argparse
import json
import logging
import os
import sys

from typing import List

from .acceptors import JsonFileLicenseAcceptor, LicenseAcceptor, accept_all
from .cache import LicenseCache, LicenseReportEntry, JsonFileLicenseCache
from .dependancies import DependancyScanner, GoModuleDependancyScanner, scan_all
from .recognizers import CommonPrefixRecognizer, GitHubRecognizer, MappedToGitHubRecognizer
from .recognizers import Recognizer, recognize_all
from .reporters import Reporter, JsonReporter, PdfReporter, report_all

_DEPENDANCY_SCANNERS = [GoModuleDependancyScanner()]


def scan(directory: str,
         dependancy_scanners: List[DependancyScanner],
         license_recognizers: List[Recognizer],
         license_acceptors: List[LicenseAcceptor] = None,
         license_reporters: List[Reporter] = None) -> (List[LicenseReportEntry],
                                                       List[LicenseReportEntry]):
    """Run a license scan on the given directory, using the given components.
       Returns a tuple with the list of all report entries and a list of report entries
       whose licenses have not been accepted.
    """

    logging.info("Checking licenses in %s", directory)
    entries = scan_all(directory, dependancy_scanners)
    recognize_all(entries, license_recognizers)
    unaccepted_entries = accept_all(entries, license_acceptors)
    if license_reporters is not None:
        report_all(entries, unaccepted_entries, license_reporters)
    return (entries, unaccepted_entries)


def main():
    """'Default' main function that parses the command line, sets up the components,
       and scans the scan method. This main function assumes that all available
       dependancy scanners and license recognizers should be used. If you need more
       control than this, including the ability to add additional scanners and
       recognizers, you will need to set them up and call scan yourself.
       """

    parser = argparse.ArgumentParser()
    parser.add_argument('--json', help='Generate a JSON license report in the given file')
    parser.add_argument('--pdf', help='Generate a PDF license report in the given file')
    parser.add_argument('--cache', help='Name of JSON license cache file (auto-created)')
    parser.add_argument('--auto-accept', help='Name of JSON auto accept file')
    parser.add_argument('--unaccepted-results',
                        help='Name of JSON file created to hold unaccepted licenses.')
    parser.add_argument('--error-on-invalid',
                        action='store_true',
                        help='Exit with the number of unrecognized or unaccepted licenses.')
    parser.add_argument('--verbose', action='store_true', help='Show debugging information')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    cache = None
    if args.cache:
        cache = JsonFileLicenseCache(args.cache)

    acceptors = None
    if args.auto_accept:
        try:
            with open(args.auto_accept) as json_file:
                json_data = json.load(json_file)
            acceptors = [JsonFileLicenseAcceptor(json_data)]
        except FileNotFoundError:
            logging.warning('Could not find %s, auto-accept ignored', args.auto_accept)
            acceptors = None

    reporters = []
    if args.json:
        reporters.append(JsonReporter(args.json))
    if args.pdf:
        reporters.append(PdfReporter(args.pdf, cache))

    (entries, unaccepted_entries) = scan(directory=os.getcwd(),
                                         dependancy_scanners=_DEPENDANCY_SCANNERS,
                                         license_recognizers=_setup_recognizers(cache),
                                         license_acceptors=acceptors,
                                         license_reporters=reporters)

    if cache is not None:
        if cache.update_cache_file():
            logging.info("The cache file %s has been changed.", args.cache)

    logging.info("Total dependancies examined: %d", len(entries))
    unaccepted_count = len(unaccepted_entries)
    if unaccepted_count > 0:
        logging.info("Number of unaccepted licenses: %d", unaccepted_count)
        _write_unaccepted_licenses(args.unaccepted_results, unaccepted_entries)
        for entry in unaccepted_entries:
            if entry.license_name is None:
                logging.info("  %s (** Unidentified **)", entry.package)
            else:
                logging.info("  %s (%s)", entry.package, entry.license_name)

    if args.error_on_invalid:
        sys.exit(unaccepted_count)


def _setup_recognizers(cache: LicenseCache) -> List[Recognizer]:
    misc_to_github_mapping = {
        'google.golang.org/appengine': 'github.com/golang/appengine',
        'google.golang.org/genproto': 'github.com/google/go-genproto',
        'google.golang.org/grpc': 'github.com/grpc/grpc-go',
        'gotest.tools': 'github.com/gotestyourself/gotest.tools',
        'honnef.co/go/tools': 'github.com/dominikh/go-tools'
    }
    go_lang_license_url = "https://raw.githubusercontent.com/golang/go/master/LICENSE"
    go_pkg_license_url = "https://raw.githubusercontent.com/niemeyer/gopkg/master/LICENSE"

    return [
        GitHubRecognizer(cache),
        MappedToGitHubRecognizer(misc_to_github_mapping, cache),
        CommonPrefixRecognizer("cloud.google.com",
                               "Apache License 2.0",
                               "http://www.apache.org/licenses/LICENSE-2.0.txt",
                               cache),
        CommonPrefixRecognizer("golang.org",
                               "Go Standard Library License",
                               go_lang_license_url,
                               cache),
        CommonPrefixRecognizer("gopkg.in", "GoPkg License", go_pkg_license_url, cache)
    ]

def _write_unaccepted_licenses(filename: str, unaccepted_entries: List[LicenseReportEntry]):
    if filename:
        logging.info("Writing unaccepted licenses to %s", filename)
        deps = []
        for entry in unaccepted_entries:
            deps.append({"moduleLicense": entry.license_name, "moduleName": entry.package})
        lics = {"dependenciesWithoutAllowedLicenses": deps}
        with open(filename, 'w') as outfile:
            json.dump(lics, outfile, indent=4)
