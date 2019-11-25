
"""Produce a report of a given set of licenses."""

import abc
import base64
import json
import logging
import sys

from typing import List, Dict

from fpdf import FPDF
import requests

from .cache import LicenseCache, LicenseReportEntry


_NEXT_LINE = 1
_FONT = "Arial"
_TITLE_SIZE = 14
_NORMAL_SIZE = 12
_LICENSE_SIZE = 11
_LINE_SIZE_MM = 5
_INDENT_MM = 10
_LICENSE_COLUMN_WIDTH_MM = 100


class Reporter(abc.ABC):
    """API for generating a report file."""

    @abc.abstractmethod
    def generate_report(self, entries: List[LicenseReportEntry]):
        """Subclasses must override this to actually generate the report."""

    @classmethod
    def generate_summary(cls, entries: List[LicenseReportEntry]) -> Dict:
        """Subclasses may use this to generate a summary of the entries by license name."""
        summary = {}
        for entry in entries:
            name = entry.license_name if entry.license_name is not None else "Other"
            if not entry.acceptable:
                name = "** Unacceptable **"
            cls._increment_counter(summary, name)
        return summary

    @classmethod
    def _increment_counter(cls, summary: Dict, lic: str):
        if lic in summary:
            summary[lic] += 1
        else:
            summary[lic] = 1


class JsonReporter(Reporter):
    """Reporter that will create a JSON file."""

    def __init__(self, filename: str):
        self.filename = filename

    def generate_report(self, entries: List[LicenseReportEntry]):
        """Generate a JSON report to the given file."""
        if self.filename == '-':
            logging.info("producing JSON report on the standard output device")
        else:
            logging.info("producing JSON report as '%s'", self.filename)
        rep = {
            'summary': self.generate_summary(entries),
            'licenses': self._generate_licenses(entries)
        }
        if self.filename == '-':
            json.dump(rep, sys.stdout, indent=4)
        else:
            with open(self.filename, 'w') as outfile:
                json.dump(rep, outfile, indent=4)

    @classmethod
    def _generate_licenses(cls, entries: List[LicenseReportEntry]):
        licenses = []
        for entry in entries:
            licenses.append({
                'package': entry.package,
                'license_name': entry.license_name,
                'license_url': entry.license_url,
                'acceptable': entry.acceptable
            })
        return licenses


class PdfReporter(Reporter):
    """Reporter that will create a PDF file."""

    def __init__(self, filename: str, cache: LicenseCache):
        self.filename = filename
        self.cache = cache

    def generate_report(self, entries: List[LicenseReportEntry]):
        """Generate a PDF report in the given filename."""
        logging.info("producing PDF report as '%s'", self.filename)
        pdf = FPDF()
        self._create_summary_page(pdf, entries)
        for entry in entries:
            self._create_license_page(pdf, entry)
        pdf.output(self.filename)

    def _create_summary_page(self, pdf: FPDF, entries: List[LicenseReportEntry]):
        logging.debug("  generating summary page")
        pdf.add_page()
        pdf.set_font(_FONT)
        pdf.set_font_size(_TITLE_SIZE)
        pdf.cell(0, _LINE_SIZE_MM*2, txt="License report", ln=_NEXT_LINE, align="C")
        pdf.ln()

        pdf.set_font_size(_NORMAL_SIZE)
        pdf.cell(0, _LINE_SIZE_MM, txt="Summary", ln=_NEXT_LINE)
        pdf.ln()

        summary = self.generate_summary(entries)
        for key in sorted(summary):
            pdf.cell(_INDENT_MM, _LINE_SIZE_MM)
            pdf.cell(_LICENSE_COLUMN_WIDTH_MM, _LINE_SIZE_MM, txt=key)
            pdf.cell(0, _LINE_SIZE_MM, txt="%d" % summary[key])
            pdf.ln()

    def _create_license_page(self, pdf: FPDF, entry: LicenseReportEntry):
        logging.debug("  generating page for %s", entry.package)
        pdf.add_page()
        pdf.set_font(_FONT)
        pdf.set_font_size(_NORMAL_SIZE)
        pdf.cell(0, _LINE_SIZE_MM, txt="Package: %s" % entry.package, ln=_NEXT_LINE)

        license_type_line = "License Type: %s" % entry.license_name
        if not entry.acceptable:
            license_type_line += " (** Unacceptable **)"
        pdf.cell(0, _LINE_SIZE_MM, txt=license_type_line, ln=_NEXT_LINE)

        pdf.cell(0, _LINE_SIZE_MM, txt="License URL: %s" % entry.license_url, ln=_NEXT_LINE)
        pdf.ln()

        pdf.cell(0, _LINE_SIZE_MM, txt="License Text", ln=_NEXT_LINE)
        pdf.ln()

        pdf.set_font_size(_LICENSE_SIZE)
        if entry.license_encoded is not None:
            text = self._b64decode(entry.license_encoded)
        elif entry.license_url is not None:
            text = self._read_text_from_url(entry.license_url, entry)
        else:
            text = "ERROR: Could not read license text"

        try:
            pdf.multi_cell(0, _LINE_SIZE_MM, txt=text)
        except UnicodeEncodeError:
            logging.error("    could not encode license as PDF")
            pdf.cell(0, _LINE_SIZE_MM, txt="Could not read text of license", ln=_NEXT_LINE)

    def _read_text_from_url(self, url: str, entry: LicenseReportEntry) -> str:
        try:
            resp = requests.get(url)
            if not self._is_ok_response(resp):
                logging.error("    bad response from %s, response=%d", url, resp.status_code)
                return "Could not read license from %s\n" % url
        except requests.ConnectionError as ex:
            logging.error("    could not read license from %s", url)
            return "Could not read license from %s.\nException=%s\n" % (url, ex)

        if not resp.headers['Content-Type'].startswith('text/plain'):
            logging.error("    could not get plain text license from %s", url)
            return "Could not read license from %s as plain text.\n" % url

        if self.cache:
            entry.license_encoded = self._b64encode(resp.text)
            self.cache.write(entry)

        return resp.text

    @classmethod
    def _b64decode(cls, txt: str) -> str:
        return base64.b64decode(txt.encode('latin-1', 'replace')).decode('latin-1', 'replace')

    @classmethod
    def _b64encode(cls, txt: str) -> str:
        return base64.b64encode(txt.encode('latin-1', 'replace')).decode('latin-1', 'replace')

    @classmethod
    def _is_ok_response(cls, resp):
        return resp.status_code >= 200 and resp.status_code < 300


def report_all(entries: List[LicenseReportEntry], reporters: List[Reporter]):
    """Generate the reports for the given list of reporters."""
    logging.info("Generating %d reports on %d entries", len(reporters), len(entries))
    for reporter in reporters:
        reporter.generate_report(entries)
