
"""Produce a report of a given set of licenses."""


import base64
import json
import logging
import sys
from typing import List, Tuple, Dict

from fpdf import FPDF
import requests

import LicenseScanner

_NEXT_LINE = 1
_FONT = "Arial"
_TITLE_SIZE = 14
_NORMAL_SIZE = 12
_LICENSE_SIZE = 11
_LINE_SIZE_MM = 5
_INDENT_MM = 10
_LICENSE_COLUMN_WIDTH_MM = 100


class Reporter:
    """Report on the given licenses."""

    def __init__(self, scanner: LicenseScanner):
        self._generate_internal_rep(scanner.licenses)


    def json_report(self, file=sys.stdout):
        """Generate a JSON report to the given file."""

        logging.info("producing JSON report")
        rep = self._rep
        for lic in rep['licenses']:
            if 'license_encoded' in lic:
                del lic['license_encoded']
        print(json.dumps(rep, indent=4), file=file)


    def pdf_report(self, filename: str, package_name: str):
        """Generate a PDF report in the given filename."""

        logging.info("producing report as '%s'", filename)
        pdf = FPDF()
        self._create_summary_page(pdf, package_name)
        for lic in self._rep['licenses']:
            Reporter._create_license_page(pdf, lic)
        pdf.output(filename)


    def _generate_internal_rep(self, licenses: List):
        rep = {'summary': {}, 'licenses': []}
        for entry in licenses:
            dep = entry[0]
            lic = entry[1]
            url = entry[2]
            valid = entry[3]
            encoded = entry[4]
            logging.debug("  %s: %s, %s", dep, lic, url)

            if not valid:
                Reporter._increment_counter(rep['summary'], '** Invalid Licenses **')
                lic += " (** Invalid **)"
            elif lic == 'Manually Accepted':
                Reporter._increment_counter(rep['summary'], 'Manually Accepted')
            else:
                Reporter._increment_counter(rep['summary'], lic)

            rep['licenses'].append({
                'package': dep,
                'license': lic,
                'license_url': url,
                'license_encoded': encoded
            })

        self._rep = rep


    @staticmethod
    def _increment_counter(summary: Dict, lic: str):
        if lic in summary:
            summary[lic] += 1
        else:
            summary[lic] = 1


    def _create_summary_page(self, pdf: FPDF, package_name: str):
        logging.debug("  generating summary page")
        pdf.add_page()
        pdf.set_font(_FONT)
        pdf.set_font_size(_TITLE_SIZE)
        title = "Third party license report for %s" % package_name
        pdf.cell(0, _LINE_SIZE_MM*2, txt=title, ln=_NEXT_LINE, align="C")
        pdf.ln()

        pdf.set_font_size(_NORMAL_SIZE)
        pdf.cell(0, _LINE_SIZE_MM, txt="Summary", ln=_NEXT_LINE)
        pdf.ln()

        for key in sorted(self._rep['summary']):
            pdf.cell(_INDENT_MM, _LINE_SIZE_MM)
            pdf.cell(_LICENSE_COLUMN_WIDTH_MM, _LINE_SIZE_MM, txt=key)
            pdf.cell(0, _LINE_SIZE_MM, txt="%d" % self._rep['summary'][key])
            pdf.ln()


    @staticmethod
    def _create_license_page(pdf: FPDF, lic: Dict):
        logging.debug("  generating page for %s", lic['package'])
        pdf.add_page()
        pdf.set_font(_FONT)
        pdf.set_font_size(_NORMAL_SIZE)
        pdf.cell(0, _LINE_SIZE_MM, txt="Package: %s" % lic['package'], ln=_NEXT_LINE)
        pdf.ln()

        pdf.cell(0, _LINE_SIZE_MM, txt="License Type: %s" % lic['license'], ln=_NEXT_LINE)
        pdf.ln()

        pdf.cell(0, _LINE_SIZE_MM, txt="License Text", ln=_NEXT_LINE)
        pdf.ln()

        pdf.set_font_size(_LICENSE_SIZE)
        if lic['license_encoded'] != None:
            text = base64.b64decode(lic['license_encoded']).decode('latin-1', 'replace')
        elif lic['license_url'] != None:
            text = Reporter._read_text_from_url(lic['license_url'])
        else:
            text = "ERROR: Could not read license text"

        try:
            pdf.multi_cell(0, _LINE_SIZE_MM, txt=text)
        except UnicodeEncodeError:
            logging.error("    could not encode license as PDF")
            pdf.cell(0, _LINE_SIZE_MM, txt="Could not read text of license", ln=_NEXT_LINE)


    @staticmethod
    def _read_text_from_url(url: str) -> str:
        try:
            resp = requests.get(url)
            if not Reporter._is_ok_response(resp):
                logging.error("    bad response from %s, response=%d", url, resp.status_code)
                return "Could not read license from %s\n" % url
        except requests.ConnectionError as ex:
            logging.error("    could not read license from %s", url)
            return "Could not read license from %s.\nException=%s\n" % (url, ex)

        try:
            j = json.loads(resp.text)
            if j['body']:
                return j['body']
        except json.decoder.JSONDecodeError:
            logging.debug("    could not interpret license as a GitHub one")

        if not resp.headers['Content-Type'].startswith('text/plain'):
            logging.error("    could not get plain text license from %s", url)
            return "Could not read license from %s as plain text.\n" % url

        return resp.text


    @staticmethod
    def _is_ok_response(resp):
        return resp.status_code >= 200 and resp.status_code < 300
