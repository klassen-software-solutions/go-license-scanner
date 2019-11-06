
"""Produce a report of a given set of licenses."""

import json
import logging
import sys
from typing import List, Tuple

import LicenseScanner


def report(scanner: LicenseScanner, file=sys.stdout):
    """Report on the given licenses, writing to the given file."""

    logging.info("producing report")
    unique = _UniqueLicenses()
    for lic in scanner.licenses:
        unique.add(lic)

    manually_accepted_count = 0
    rep = {'summary': {}, 'licenses': []}
    for entry in unique.get_sorted():
        lic = entry[0]
        url = entry[1]
        deps = entry[2]
        logging.debug("  %s, %s", lic, url)
        for value in deps:
            logging.debug("    %s", value)

        if lic == 'Manually Accepted':
            manually_accepted_count += len(deps)
        else:
            rep['summary'][lic] = len(deps)

        rep['licenses'].append({'name': lic, 'url': url, 'used-by': deps})

    if manually_accepted_count > 0:
        rep['summary']['Manually Accepted'] = manually_accepted_count

    invalid_license_count = scanner.count_invalid_licenses()
    if invalid_license_count > 0:
        rep['summary']['Invalid Licenses'] = invalid_license_count

    print(json.dumps(rep, indent=4), file=file)


class _UniqueLicenses:
    def __init__(self):
        self.licenses = {}

    def add(self, lic: Tuple):
        """Add a dependancy to the license collection."""

        key = (lic[LicenseScanner.LICENSE_ABBREVIATION_COLUMN],
               lic[LicenseScanner.URL_COLUMN])
        dep = lic[LicenseScanner.DEPENDANCY_COLUMN]
        if key not in self.licenses:
            self.licenses[key] = []
        self.licenses[key].append(dep)

    def get_sorted(self) -> List:
        """Return the internal object as a sorted list of license, url, list of
           dependancies.
        """
        lst = []
        for key in sorted(self.licenses):
            entry = (key[0], key[1], sorted(self.licenses[key]))
            lst.append(entry)
        return lst
