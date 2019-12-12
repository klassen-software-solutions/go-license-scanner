
import tempfile
import unittest

from license_scanner.cache import LicenseReportEntry, JsonFileLicenseCache


class TestJsonFileLicenseCache(unittest.TestCase):

    def test_cache_read_and_write(self):
        ch = JsonFileLicenseCache("/tmp/no-file-needed-for-this-test")
        self.assertIsNone(ch.read("my package name"))

        ch.write(LicenseReportEntry(package="my package name", license_name="license"))
        self.assertEqual(ch.read("my package name"),
                         LicenseReportEntry(package="my package name",
                                            license_name="license"))

        l = ch.read("my package name")
        l.license_url = "http://no.such.machine/"
        ch.write(l)
        self.assertEqual(ch.read("my package name"),
                         LicenseReportEntry(package="my package name",
                                            license_name="license",
                                            license_url="http://no.such.machine/"))

    def test_file_write_and_restore(self):
        filename = _temp_filename()
        _setup_file(filename)
        ch = JsonFileLicenseCache(filename)
        self.assertIsNone(ch.read("not there"))
        self.assertEqual(ch.read("one"), LicenseReportEntry(package="one"))
        self.assertEqual(ch.read("two"), LicenseReportEntry(package="two"))


def _setup_file(filename: str):
    ch = JsonFileLicenseCache(filename)
    ch.write(LicenseReportEntry(package="one"))
    ch.write(LicenseReportEntry(package="two"))
    ch.update_cache_file()

def _temp_filename() -> str:
    tf = tempfile.NamedTemporaryFile(prefix="/tmp/license-scanner-cache-test")
    name = tf.name
    tf.close()
    return name
