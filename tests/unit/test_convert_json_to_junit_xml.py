import json
import os
import tempfile
import xml.etree.ElementTree as ET
import pytest
from pathlib import Path

from pytest_reporter_plus.json_to_xml_converter import convert_json_to_junit_xml, sanitize_classname


@pytest.mark.skip(reason="Skipping for test coverage")
def test_skipped_example():
    assert True

@pytest.fixture
def sample_json_file():
    test_data = [
        {
            "test": "test_login",
            "nodeid": "tests/test_auth.py::test_login",
            "status": "failed",
            "duration": 0.25,
            "error": "AssertionError: login failed",
            "markers": ["smoke", "auth"],
            "file": "tests/test_auth.py",
            "line": 42,
            "stdout": "Login attempt started\n",
            "stderr": "Traceback (most recent call...)",
            "timestamp": "2025-07-04T12:00:00Z",
            "screenshot": "http://example.com/screen1.png",
            "logs": ["POST /login", "200 OK"],
            "worker": "main",
            "links": ["http://example.com/login-trace"],
            "flaky": False
        }
    ]

    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as tmp:
        json.dump(test_data, tmp)
        tmp_path = tmp.name

    yield tmp_path
    os.remove(tmp_path)


def test_convert_json_to_xml(sample_json_file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp_xml:
        xml_path = tmp_xml.name

    try:
        convert_json_to_junit_xml(sample_json_file, xml_path)
        assert os.path.exists(xml_path)

        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Verify <testsuite> tag
        assert root.tag == "testsuite"
        assert root.attrib["tests"] == "1"

        # Verify <testcase> tag
        testcase = root.find("testcase")
        assert testcase is not None
        assert testcase.attrib["classname"] == "tests.test_auth"
        assert testcase.attrib["name"] == "test_login"
        assert testcase.attrib["time"] == "0.25"
        assert testcase.attrib["worker"] == "main"
        assert testcase.attrib["timestamp"] == "2025-07-04T12:00:00Z"
        assert testcase.attrib["line"] == "42"
        assert testcase.attrib["flaky"] == "false"

        # Verify <failure>
        failure = testcase.find("failure")
        assert failure is not None
        assert "AssertionError" in failure.attrib["type"]
        assert "login failed" in failure.attrib["message"]

        # Verify <system-out> and <system-err>
        assert testcase.find("system-out").text.startswith("Login")
        assert "Traceback" in testcase.find("system-err").text

        # Verify <properties>
        properties = testcase.find("properties")
        assert properties is not None

        prop_names = [prop.attrib["name"] for prop in properties.findall("property")]
        assert "marker" in prop_names
        assert "link" in prop_names
        assert "screenshot" in prop_names
        assert "log" in prop_names

    finally:
        if os.path.exists(xml_path):
            os.remove(xml_path)

@pytest.mark.parametrize("filepath, expected", [
    ("tests/test_login.py", "tests.test_login"),
    ("tests\\test_user.py", "tests.test_user"),       # Windows path
    ("tests/utils/helpers.py", "tests.utils.helpers"),
    (None, "default"),                                # Missing value
    ("", "default"),                                  # Empty string
])
def test_sanitize_classname(filepath, expected):
    assert sanitize_classname(filepath) == expected