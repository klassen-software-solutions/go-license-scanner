
import tempfile
import json
import unittest

import license_scanner.reporters as reporters
from license_scanner.cache import LicenseReportEntry


_CORRECT_LICENSE_ARRAY = [
    {
        'moduleName': 'cloud.google.com',
        'moduleLicense': 'Apache License 2.0',
        'moduleLicenseUrl': 'http://www.apache.org/licenses/LICENSE-2.0.txt'
    },
    {
        'moduleName': 'github.com/Azure/go-ansiterm',
        'moduleLicense': 'MIT License',
        'moduleLicenseUrl': 'https://raw.githubusercontent.com/Azure/go-ansiterm/master/LICENSE'
    },
    {
        'moduleName': 'github.com/Flaque/filet',
        'moduleLicense': 'Apache License 2.0',
        'moduleLicenseUrl': 'http://www.apache.org/licenses/LICENSE-2.0.txt'
    },
    {
        'moduleName': 'github.com/cenkalti/backoff',
        'moduleLicense': 'MIT License',
        'moduleLicenseUrl': 'https://raw.githubusercontent.com/cenkalti/backoff/v3/LICENSE'
    },
    {
        'moduleName': 'github.com/client9/misspell',
        'moduleLicense': 'MIT License',
        'moduleLicenseUrl': 'https://raw.githubusercontent.com/client9/misspell/master/LICENSE'
    }
]

class TestJsonReporter(unittest.TestCase):

    def test_json_report(self):
        entries = [
            LicenseReportEntry(package='cloud.google.com',
                               license_name='Apache License 2.0',
                               license_url='http://www.apache.org/licenses/LICENSE-2.0.txt'),
            LicenseReportEntry(package='github.com/Azure/go-ansiterm',
                               license_name='MIT License',
                               license_url='https://raw.githubusercontent.com/Azure/go-ansiterm/master/LICENSE'),
            LicenseReportEntry(package='github.com/Flaque/filet',
                               license_name='Apache License 2.0',
                               license_url='http://www.apache.org/licenses/LICENSE-2.0.txt'),
            LicenseReportEntry(package='github.com/cenkalti/backoff',
                               license_name='MIT License',
                               license_url='https://raw.githubusercontent.com/cenkalti/backoff/v3/LICENSE'),
            LicenseReportEntry(package='github.com/client9/misspell',
                               license_name='MIT License',
                               license_url='https://raw.githubusercontent.com/client9/misspell/master/LICENSE')
        ]
        unaccepted = [
            LicenseReportEntry(package='cloud.google.com',
                               license_name='Apache License 2.0',
                               license_url='http://www.apache.org/licenses/LICENSE-2.0.txt'),
            LicenseReportEntry(package='github.com/Flaque/filet',
                               license_name='Apache License 2.0',
                               license_url='http://www.apache.org/licenses/LICENSE-2.0.txt')
        ]

        filename = _temp_filename()
        reporters.report_all(entries, unaccepted, [reporters.JsonReporter(filename)])

        with open(filename) as json_file:
            data = json.load(json_file)

        self.assertEqual(1, len(data))
        self.assertEqual(data['dependencies'], _CORRECT_LICENSE_ARRAY)


def _temp_filename() -> str:
    tf = tempfile.NamedTemporaryFile(prefix="/tmp/license-scanner-reporter-test")
    name = tf.name
    tf.close()
    return name
