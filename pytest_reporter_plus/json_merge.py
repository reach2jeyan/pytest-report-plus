import json
import os
from collections import defaultdict


def merge_json_reports(directory=".pytest_worker_jsons", output_path="final_report.json"):
    all_tests = []
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".json"):
            filepath = os.path.join(directory, filename)
            with open(filepath) as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_tests.extend(data)
                    elif isinstance(data, dict) and "results" in data:
                        all_tests.extend(data["results"])
                except Exception as e:
                    print(f"Could not parse {filename}: {e}")

    # Group tests by nodeid
    tests_by_nodeid = defaultdict(list)
    for test in all_tests:
        nodeid = test.get("nodeid") or test.get("test")  # fallback if needed
        tests_by_nodeid[nodeid].append(test)

    # Create merged results with flaky info
    merged_results = []
    for nodeid, attempts in tests_by_nodeid.items():
        # Take last attempt as final
        final_test = attempts[-1].copy()
        final_test["flaky"] = len(attempts) > 1
        final_test["flaky_attempts"] = [t.get("status") for t in attempts]
        merged_results.append(final_test)

    try:
        with open(output_path, "w") as f:
            json.dump(merged_results, f, indent=2)
    except Exception as e:
        print(f" Failed to write merged report to {output_path}: {e}")
