"""Tests for LLM request handling."""

import unittest
from unittest import mock

import requests

import extractor


class OllamaRequestTests(unittest.TestCase):
    def test_http_error_includes_ollama_response_detail(self):
        response = mock.Mock()
        response.text = '{"error":"model requires more available memory"}'
        response.raise_for_status.side_effect = requests.HTTPError(
            "500 Server Error"
        )

        with mock.patch.object(extractor.requests, "post", return_value=response):
            with self.assertRaisesRegex(
                requests.HTTPError, "model requires more available memory"
            ):
                extractor._call_ollama("prompt", [("field", "text")])

    def test_http_error_detail_is_capped(self):
        response = mock.Mock()
        response.text = "x" * 1200
        response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")

        with mock.patch.object(extractor.requests, "post", return_value=response):
            with self.assertRaises(requests.HTTPError) as caught:
                extractor._call_ollama("prompt", [("field", "text")])

        self.assertLessEqual(len(str(caught.exception)), len("500 Server Error") + 1020)


if __name__ == "__main__":
    unittest.main()