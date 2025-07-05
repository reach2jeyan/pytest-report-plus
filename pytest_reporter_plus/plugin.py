import shutil
import webbrowser
from pathlib import Path

import pytest

from pytest_reporter_plus.extract_link import extract_links_from_item
from pytest_reporter_plus.generate_html_report import JSONReporter
from pytest_reporter_plus.json_merge import merge_json_reports
from pytest_reporter_plus.json_to_xml_converter import convert_json_to_junit_xml
from pytest_reporter_plus.resolver_driver import take_screenshot_generic, resolve_driver
from pytest_reporter_plus.send_email_report import send_email_from_env, load_email_env

python_executable = shutil.which("python3") or shutil.which("python")
test_screenshot_paths = {}

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    if "caplog" not in item.fixturenames:
        item.fixturenames.append("caplog")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" or (report.when == "setup" and report.skipped):
        config = item.config
        capture_option = config.getoption("--capture-screenshots")

        caplog_text = None
        if "caplog" in item.funcargs:
            caplog = item.funcargs["caplog"]
            caplog_text = "\n".join(caplog.messages) if caplog.messages else None

        screenshot_path = None

        should_capture_screenshot = (
                capture_option == "all" or
                (capture_option == "failed" and report.outcome == "failed")
        )

        if should_capture_screenshot:
            driver = resolve_driver(item)
            if driver:
                try:
                    screenshot_path = take_screenshot_generic(item, driver)
                except Exception as e:
                    print(f"Failed to capture screenshot: {e}")

        reporter = config._json_reporter
        worker_id = os.getenv("PYTEST_XDIST_WORKER") or "main"
        reporter.log_result(
            test_name=item.name,
            nodeid=item.nodeid,
            status=report.outcome,
            duration=report.duration,
            error=str(report.longrepr) if report.failed else None,
            markers=[m.name for m in item.iter_markers()],
            filepath=item.location[0],
            lineno=item.location[1],
            stdout=getattr(report, "capstdout", ""),
            stderr=getattr(report, "capstderr", ""),
            screenshot=screenshot_path,
            logs=caplog_text,
            worker=worker_id,
            links=extract_links_from_item(item)
        )


import subprocess


def pytest_sessionfinish(session, exitstatus):
    reporter = session.config._json_reporter

    json_path = session.config.getoption("--json-report") or "final_report.json"
    html_output = session.config.getoption("--html-output") or "report_output"
    screenshots = session.config.getoption("--screenshots") or "screenshots"
    xml_path = session.config.getoption("--xml-report") or "final_xml.xml"

    is_worker = os.getenv("PYTEST_XDIST_WORKER") is not None
    try:
        is_xdist = bool(session.config.getoption("-n"))
    except ValueError:
        is_xdist = False

    if is_worker:
        reporter.write_report()
        print(f"Worker {os.getenv('PYTEST_XDIST_WORKER')} finished – skipping merge.")
        return

    if is_xdist:
        merge_json_reports(directory=".pytest_worker_jsons", output_path=json_path)
    else:
        reporter.results = mark_flaky_tests(reporter.results)
        reporter.write_report()

    script_path = os.path.join(os.path.dirname(__file__), "generate_html_report.py")

    if not os.path.exists(script_path):
        print(f"Warning: Report generation script not found at {script_path}. Skipping HTML report generation.")
        return

    try:
        subprocess.run([
            sys.executable,
            script_path,
            "--report", json_path,
            "--screenshots", screenshots,
            "--output", html_output
        ], check=True)
    except Exception as e:
        print(f"Exception during HTML report generation: {e}")

    if session.config.getoption("--send-email"):
        print("📬 --send-email enabled. Sending report...")
        try:
            config = load_email_env()
            send_email_from_env(config)
        except Exception as e:
            print(f"Failed to send email: {e}")

    open_html_report(report_path=f"{html_output}/report.html",json_path=json_path, config=session.config)

    if session.config.getoption("--generate-xml"):
        try:
            json_path = reporter.report_path
            convert_json_to_junit_xml(json_path, xml_path)
            print(f"XML report generated: {xml_path}")
        except Exception as e:
            print(f"Failed to generate XML report: {e}")


def pytest_sessionstart(session):
    configure_logging()
    session.config.addinivalue_line(
        "markers", "link(url): Add a link to external test case or documentation."
    )


def pytest_load_initial_conftests(args):
    if not any(arg.startswith("--capture") for arg in args):
        args.append("--capture=tee-sys")


def pytest_addoption(parser):
    parser.addoption(
        "--json-report",
        action="store",
        default="final_report.json",
        help="Directory to save individual JSON test reports"
    )
    parser.addoption(
        "--capture-screenshots",
        action="store",
        default="failed",
        choices=["failed", "all", "none"],
        help="Capture screenshots: failed (default), all, or none"
    )
    parser.addoption("--html-output", default="report_output")
    parser.addoption("--screenshots", default="screenshots")
    parser.addoption(
        "--send-email",
        action="store_true",
        default=False,
        help="Send HTML test report via email after test run"
    )
    parser.addoption(
        "--detect-flake",
        action="store",
        default=False,
        help="Helps capture flaky tests in the last n number of builds"
    )
    parser.addoption(
        "--should-open-report",
        action="store",
        default="failed",
        choices=["always", "failed", "never"],
        help="When to open the HTML report: always, failed, or never (default: failed)",
    )
    parser.addoption(
        "--generate-xml",
        action="store_true",
        default=False,
        help="Generate JUnit-style XML from the final JSON report"
    )
    parser.addoption(
        "--xml-report",
        action="store",
        default=None,
        help="Path to output the XML report (used with --generatexml)"
    )


def take_screenshot_on_failure(item, page):
    screenshot_dir = os.path.join(os.getcwd(), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    filename = f"{item.name}.png".replace("/", "_").replace("\\", "_")
    path = os.path.join(screenshot_dir, filename)
    page.screenshot(path=path)
    return path


def take_screenshot_selenium(item, driver):
    screenshot_dir = os.path.join(os.getcwd(), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    filename = f"{item.name}.png".replace("/", "_").replace("\\", "_")
    path = os.path.join(screenshot_dir, filename)
    driver.save_screenshot(path)
    return path


import logging
import sys


def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def pytest_configure(config):
    global _saved_config
    _saved_config = config

    INTERNAL_JSON_DIR = Path(".pytest_worker_jsons")
    report_path = config.getoption("--json-report") or "final_report.json"
    worker_id = os.getenv("PYTEST_XDIST_WORKER")

    if worker_id:
        INTERNAL_JSON_DIR.mkdir(parents=True, exist_ok=True)
        name, ext = os.path.splitext(report_path)
        report_path = INTERNAL_JSON_DIR / f"{name}_{worker_id}{ext}"

    config._json_reporter = JSONReporter(report_path=report_path)


def pytest_collectreport(report):
    if report.failed:
        global _saved_config
        reporter = getattr(_saved_config, "_json_reporter", None)
        if reporter:
            reporter.log_result(
                test_name="COLLECTION ERROR",
                nodeid=str(report.nodeid),
                status="error",
                duration=getattr(report, "duration", 0.0),
                error=str(report.longrepr),
                markers=[],
                filepath=str(report.fspath),
                lineno=0,
                stdout="",
                stderr="",
                screenshot=None,
                logs=None,
                worker=os.getenv("PYTEST_XDIST_WORKER") or "main"
            )


import os


def mark_flaky_tests(results):
    # Group test attempts by nodeid
    tests_by_nodeid = {}
    for test in results:
        tests_by_nodeid.setdefault(test["nodeid"], []).append(test)

    # Only return the final test attempt with flaky info
    final_results = []
    for nodeid, attempts in tests_by_nodeid.items():
        final_test = attempts[-1].copy()

        previous_statuses = [t["status"] for t in attempts[:-1]]
        final_status = final_test["status"]

        # A test is flaky if it passed at the end but had at least one failure before
        if final_status == "passed" and "failed" in previous_statuses:
            final_test["flaky"] = True
            final_test["flaky_attempts"] = [t["status"] for t in attempts]
        else:
            final_test["flaky"] = False

        final_results.append(final_test)

    return final_results

def open_html_report(report_path, json_path, config):
   should_open = config.getoption("--should-open-report", default="failed").lower()

   if not report_path or not os.path.exists(report_path):
       return

   try:
       with open(json_path, "r") as f:
           import json
           report_data = json.load(f)

       has_failures = any(
           t.get("status") == "failed" or t.get("error")
           for t in report_data
       )

       if should_open == "always" or (should_open == "failed" and has_failures):
           webbrowser.open(f"file://{os.path.abspath(report_path)}")

   except Exception as e:
       print(f"Could not open report: {e}")

