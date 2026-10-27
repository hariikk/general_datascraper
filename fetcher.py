"""
fetcher.py — get the full text of a paper, open-access only.

Tries, in order:
  1. PMC Open Access  (if the paper has a PMCID)
  2. an open-access URL the search source already gave us (Europe PMC / Crossref)
  3. Unpaywall          (looks up the DOI and, if it's open access, gives a PDF/URL)

If none succeed, returns (None, reason) and the paper is logged as closed-source.
Only returns text that is plausibly a real article body (>= 500 characters).
"""

import io
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import requests

import config

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
MIN_TEXT_CHARS = 500


def fetch_full_text(paper):
    """Return (text, source) or (None, reason)."""
    pmcid = paper.get("pmcid") or ""
    if pmcid:
        text = _fetch_pmc_xml(pmcid)
        if _good(text):
            return text, "pmc-open-access"

    url = paper.get("fulltext_url") or ""
    if url:
        text = _fetch_url_text(url)
        if _good(text):
            return text, "open-access-url"

    doi = paper.get("doi") or ""
    if doi:
        text = _fetch_unpaywall(doi)
        if _good(text):
            return text, "unpaywall"

    return None, "closed (no open-access full text found)"


def _good(text):
    return bool(text) and len(text.strip()) >= MIN_TEXT_CHARS


# --- 1. PMC Open Access (XML body) ----------------------------------------

def _fetch_pmc_xml(pmcid):
    params = {
        "db": "pmc",
        "id": pmcid,
        "rettype": "xml",
        "retmode": "xml",
        "tool": "general-datascraper",
        "email": config.NCBI_EMAIL,
    }
    try:
        r = requests.get(EFETCH, params=params, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        body = root.find(".//body")
        if body is None:
            return ""
        return " ".join(body.itertext()).strip()
    except Exception:
        return ""


# --- 2/3. Generic URL fetch (PDF or HTML) ----------------------------------

def _fetch_url_text(url):
    try:
        r = requests.get(url, headers=config.HTTP_HEADERS, timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
    except Exception:
        return ""
    ctype = r.headers.get("Content-Type", "")
    if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
        return _pdf_to_text(r.content)
    return _html_to_text(r.text)


def _pdf_to_text(content):
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def _html_to_text(html):
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    return re.sub(r"\s+", " ", " ".join(p.parts)).strip()


# --- Unpaywall (DOI -> open-access location) --------------------------------

def _fetch_unpaywall(doi):
    params = {"email": config.NCBI_EMAIL}
    try:
        r = requests.get(f"https://api.unpaywall.org/v2/{doi}", params=params,
                         timeout=config.HTTP_TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return ""
    if not data.get("is_oa"):
        return ""
    loc = data.get("best_oa_location") or {}
    url = loc.get("url_for_pdf") or loc.get("url") or ""
    if not url:
        return ""
    return _fetch_url_text(url)
