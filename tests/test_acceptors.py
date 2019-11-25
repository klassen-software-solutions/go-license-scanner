
import unittest

import license_scanner.acceptors as acceptors
from license_scanner.cache import LicenseReportEntry


class TestJsonFileLicenseAcceptor(unittest.TestCase):
    def setUp(self):
        json_data = {
            "acceptable-license-types": ["good1", "good2"],
            "unacceptable-license-types": ["bad"]
        }
        self.acceptor = acceptors.JsonFileLicenseAcceptor(json_data, cache=None)
        self.entries = [
            _entry("one", "good1"),
            _entry("two", "good2"),
            _entry("three", "bad"),
            _entry("four", "unknown"),
            _entry("five", "good1", False, "my name"),
            _entry("six", "bad", True, "my name")
        ]

    def test_no_acceptors(self):
        acceptors.accept_all(self.entries, [])
        self.assertEqual(self.entries[0], _entry("one", "good1", None, None))
        self.assertEqual(self.entries[1], _entry("two", "good2", None, None))
        self.assertEqual(self.entries[2], _entry("three", "bad", None, None))
        self.assertEqual(self.entries[3], _entry("four", "unknown", None, None))
        self.assertEqual(self.entries[4], _entry("five", "good1", False, "my name"))
        self.assertEqual(self.entries[5], _entry("six", "bad", True, "my name"))

    def test_one_acceptor(self):
        acceptors.accept_all(self.entries, [self.acceptor])
        self.assertEqual(self.entries[0], _entry("one", "good1", True, "JsonFileLicenseAcceptor"))
        self.assertEqual(self.entries[1], _entry("two", "good2", True, "JsonFileLicenseAcceptor"))
        self.assertEqual(self.entries[2], _entry("three", "bad", False, "JsonFileLicenseAcceptor"))
        self.assertEqual(self.entries[3], _entry("four", "unknown", None, None))
        self.assertEqual(self.entries[4], _entry("five", "good1", False, "my name"))
        self.assertEqual(self.entries[5], _entry("six", "bad", True, "my name"))

    def test_two_acceptors(self):
        acceptors.accept_all(self.entries, [_DummyAcceptor(), self.acceptor])
        self.assertEqual(self.entries[0], _entry("one", "good1", True, "JsonFileLicenseAcceptor"))
        self.assertEqual(self.entries[1], _entry("two", "good2", True, "_DummyAcceptor"))
        self.assertEqual(self.entries[2], _entry("three", "bad", True, "_DummyAcceptor"))
        self.assertEqual(self.entries[3], _entry("four", "unknown", False, "_DummyAcceptor"))
        self.assertEqual(self.entries[4], _entry("five", "good1", False, "my name"))
        self.assertEqual(self.entries[5], _entry("six", "bad", True, "my name"))


class _DummyAcceptor(acceptors.LicenseAcceptor):
    def __init__(self):
        acceptors.LicenseAcceptor.__init__(self, cache=None)

    def do_accept_or_reject(self, entry: LicenseReportEntry) -> bool:
        if entry.package[0] == 't':
            entry.acceptable = True
            entry.acceptor_name = type(self).__name__
            return True
        elif entry.package[0] == 'f':
            entry.acceptable = False
            entry.acceptor_name = type(self).__name__
            return True
        return None


def _entry(package: str, license_name: str, acceptable: bool = None, name: str = None):
    return LicenseReportEntry(package=package,
                              license_name=license_name,
                              acceptable=acceptable,
                              acceptor_name = name)
