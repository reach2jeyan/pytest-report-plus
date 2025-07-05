import pytest

from pytest_reporter_plus.plugin import mark_flaky_tests


class TestMarkFlakyTests:

    def test_single_non_flaky_test(self):
        results = [
            {"nodeid": "test_sample.py::test_a", "status": "passed"}
        ]
        marked = mark_flaky_tests(results)
        assert len(marked) == 1
        assert marked[0]["nodeid"] == "test_sample.py::test_a"
        assert marked[0]["flaky"] is False
        assert "flaky_attempts" not in marked[0]

    def test_flaky_test_with_multiple_attempts(self):
        results = [
            {"nodeid": "test_sample.py::test_b", "status": "failed"},
            {"nodeid": "test_sample.py::test_b", "status": "passed"},
        ]
        marked = mark_flaky_tests(results)
        assert len(marked) == 1
        test = marked[0]
        assert test["nodeid"] == "test_sample.py::test_b"
        assert test["status"] == "passed"
        assert test["flaky"] is True
        assert test["flaky_attempts"] == ["failed", "passed"]

    def test_mixed_tests_flaky_and_non_flaky(self):
        results = [
            {"nodeid": "test_sample.py::test_x", "status": "failed"},
            {"nodeid": "test_sample.py::test_x", "status": "passed"},
            {"nodeid": "test_sample.py::test_y", "status": "passed"},
        ]
        marked = mark_flaky_tests(results)
        assert len(marked) == 2

        by_nodeid = {t["nodeid"]: t for t in marked}

        # test_x is flaky
        assert by_nodeid["test_sample.py::test_x"]["flaky"] is True
        assert by_nodeid["test_sample.py::test_x"]["flaky_attempts"] == ["failed", "passed"]

        # test_y is not flaky
        assert by_nodeid["test_sample.py::test_y"]["flaky"] is False
        assert "flaky_attempts" not in by_nodeid["test_sample.py::test_y"]

    def test_preserves_other_fields(self):
        results = [
            {"nodeid": "test_sample.py::test_meta", "status": "failed", "duration": 0.3},
            {"nodeid": "test_sample.py::test_meta", "status": "passed", "duration": 0.2},
        ]
        marked = mark_flaky_tests(results)
        assert len(marked) == 1
        assert marked[0]["duration"] == 0.2  # last attempt
        assert marked[0]["flaky"] is True
        assert marked[0]["flaky_attempts"] == ["failed", "passed"]

    def test_multiple_failures_not_flaky(self):
        results = [
            {"nodeid": "test_sample.py::test_fail", "status": "failed"},
            {"nodeid": "test_sample.py::test_fail", "status": "failed"},
        ]
        marked = mark_flaky_tests(results)
        assert len(marked) == 1
        assert marked[0]["flaky"] is False
        assert "flaky_attempts" not in marked[0]

    def test_multiple_passes_not_flaky(self):
        results = [
            {"nodeid": "test_sample.py::test_pass", "status": "passed"},
            {"nodeid": "test_sample.py::test_pass", "status": "passed"},
        ]
        marked = mark_flaky_tests(results)
        assert len(marked) == 1
        assert marked[0]["flaky"] is False
        assert "flaky_attempts" not in marked[0]
