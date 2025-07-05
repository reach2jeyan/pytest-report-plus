import json
import subprocess
import textwrap


def test_passing_test_logged_even_if_screenshot_not_taken(tmp_path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(textwrap.dedent("""
        def test_always_passes():
            assert True
    """))

    report_file = tmp_path / "report.json"
    result = subprocess.run(
        [
            "pytest",
            str(test_file),
            "--capture-screenshots=failed",
            f"--json-report={report_file}"
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Pytest failed:\n{result.stderr}\n{result.stdout}"
    assert report_file.exists(), "Report file not created"

    data = json.loads(report_file.read_text())
    found_test = any(t["nodeid"].endswith("test_always_passes") for t in data)

    assert found_test, "Passing test not logged in JSON report"
