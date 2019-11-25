
import tempfile
import json
import unittest

import license_scanner.reporters as reporters
from license_scanner.cache import LicenseReportEntry


_CORRECT_SUMMARY = {
    '** Unacceptable **': 2,
    'MIT License': 3
 }

_CORRECT_LICENSE_ARRAY = [
    {
        'package': 'cloud.google.com',
        'license_name': 'Apache License 2.0',
        'license_url': 'http://www.apache.org/licenses/LICENSE-2.0.txt',
        'acceptable': False
    },
    {
        'package': 'github.com/Azure/go-ansiterm',
        'license_name': 'MIT License',
        'license_url': 'https://raw.githubusercontent.com/Azure/go-ansiterm/master/LICENSE',
        'acceptable': True
    },
    {
        'package': 'github.com/Flaque/filet',
        'license_name': 'Apache License 2.0',
        'license_url': 'http://www.apache.org/licenses/LICENSE-2.0.txt',
        'acceptable': None
    },
    {
        'package': 'github.com/cenkalti/backoff',
        'license_name': 'MIT License',
        'license_url': 'https://raw.githubusercontent.com/cenkalti/backoff/v3/LICENSE',
        'acceptable': True
    },
    {
        'package': 'github.com/client9/misspell',
        'license_name': 'MIT License',
        'license_url': 'https://raw.githubusercontent.com/client9/misspell/master/LICENSE',
        'acceptable': True
    }
]

class TestJsonReporter(unittest.TestCase):

    def test_json_report(self):
        entries = [
            LicenseReportEntry(package='cloud.google.com',
                               license_name='Apache License 2.0',
                               license_url='http://www.apache.org/licenses/LICENSE-2.0.txt',
                               acceptable=False),
            LicenseReportEntry(package='github.com/Azure/go-ansiterm',
                               license_name='MIT License',
                               license_url='https://raw.githubusercontent.com/Azure/go-ansiterm/master/LICENSE',
                               acceptable=True),
            LicenseReportEntry(package='github.com/Flaque/filet',
                               license_name='Apache License 2.0',
                               license_url='http://www.apache.org/licenses/LICENSE-2.0.txt'),
            LicenseReportEntry(package='github.com/cenkalti/backoff',
                               license_name='MIT License',
                               license_url='https://raw.githubusercontent.com/cenkalti/backoff/v3/LICENSE',
                               acceptable=True),
            LicenseReportEntry(package='github.com/client9/misspell',
                               license_name='MIT License',
                               license_url='https://raw.githubusercontent.com/client9/misspell/master/LICENSE',
                               acceptable=True)
        ]

        filename = _temp_filename()
        reporters.report_all(entries, [reporters.JsonReporter(filename)])

        with open(filename) as json_file:
            data = json.load(json_file)

        self.assertEqual(2, len(data))
        self.assertEqual(data['summary'], _CORRECT_SUMMARY)
        self.assertEqual(data['licenses'], _CORRECT_LICENSE_ARRAY)


def _temp_filename() -> str:
    tf = tempfile.NamedTemporaryFile(prefix="/tmp/license-scanner-reporter-test")
    name = tf.name
    tf.close()
    return name
