
import unittest
from typing import Dict, List

import license_scanner.acceptors as acceptors
from license_scanner.cache import LicenseReportEntry


class TestJsonFileLicenseAcceptor(unittest.TestCase):
    def setUp(self):
        json_data = {
            "allowedLicenses": [
                { "moduleLicense": "good1" },
                { "moduleLicense": "good2" },
                { "moduleLicense": "unknown", "moduleName": "seven" },
                { "moduleLicense": "unknown", "moduleName": "ei*" },
                { "moduleLicense": "unknown", "moduleName": "nine.a*" }
            ]
        }
        self.acceptor = acceptors.JsonFileLicenseAcceptor(json_data)
        self.entries = [
            _entry("one", "good1"),
            _entry("two", "good2"),
            _entry("three", "bad"),
            _entry("four", "unknown"),
            _entry("seven", "unknown"),
            _entry("eight", "unknown"),
            _entry("nine.aaa", "unknown"),
            _entry("ninexaaa", "unknown")
        ]

    def test_no_acceptors(self):
        unaccepted = acceptors.accept_all(self.entries, [])
        self.assertEqual(unaccepted, self.entries)

    def test_one_acceptor(self):
        unaccepted = _to_package_list(acceptors.accept_all(self.entries, [self.acceptor]))
        self.assertEqual(unaccepted, ["three", "four", "ninexaaa"])

    def test_two_acceptors(self):
        unaccepted = _to_package_list(acceptors.accept_all(self.entries,
                                                           [_DummyAcceptor(), self.acceptor]))
        self.assertEqual(unaccepted, ["four", "ninexaaa"])


class _DummyAcceptor(acceptors.LicenseAcceptor):
    def accept_or_reject(self, entry: LicenseReportEntry) -> bool:
        if entry.package[0] == 't':
            return True
        elif entry.package[0] == 'f':
            return False
        return None


def _entry(package: str, license_name: str):
    return LicenseReportEntry(package=package, license_name=license_name)

def _to_package_list(entries: List[LicenseReportEntry]) -> List[str]:
    packages = []
    for entry in entries:
        packages.append(entry.package)
    return packages
