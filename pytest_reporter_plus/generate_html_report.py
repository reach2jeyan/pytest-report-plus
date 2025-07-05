import argparse
import json
import os
import shutil
from datetime import datetime
import html


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from Playwright JSON report")
    parser.add_argument("--report", required=True, help="Path to the JSON report file")
    parser.add_argument("--screenshots", default="screenshots", help="Folder path where screenshots are saved")
    parser.add_argument("--output", default="report_output", help="Output folder for HTML report")
    args = parser.parse_args()

    reporter = JSONReporter(
        report_path=args.report,
        screenshots_dir=args.screenshots,
        output_dir=args.output,
    )
    reporter.load_report()
    reporter.generate_html_report()


class JSONReporter:
    def __init__(self, report_path="final_report.json", screenshots_dir="screenshots", output_dir="report_output"):
        self.parsed_data = None
        self.report_path = report_path
        self.screenshots_dir = screenshots_dir
        self.output_dir = output_dir
        self.results = []
        all_markers = set()
        for test in self.results:
            for marker in test.get("markers", []):
                all_markers.add(marker)
        all_markers = sorted(all_markers)

    def load_report(self):
        with open(self.report_path) as f:
            self.results = json.load(f)

    def log_result(
            self,
            test_name,
            nodeid,
            status,
            duration,
            error=None,
            markers=None,
            filepath=None,
            lineno=None,
            stdout=None,
            stderr=None,
            screenshot=None,
            logs=None,
            worker=None,
            links=None
    ):
        result = {
            "test": test_name,
            "nodeid": nodeid,
            "status": status,
            "duration": duration,
            "error": error,
            "markers": markers or [],
            "file": filepath,
            "line": lineno,
            "stdout": stdout,
            "stderr": stderr,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "screenshot": screenshot,
            "logs": logs or [],
            "worker": worker,
            "links": links
        }
        if error:
            result["error"] = error
        self.results.append(result)

    def write_report(self):
        dir_path = os.path.dirname(os.path.abspath(self.report_path))

        # Ensure directory exists
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        try:
            with open(self.report_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2)
        except Exception as e:
            print(f"Failed to write JSON report ")

    def copy_all_screenshots(self):
        screenshots_output_dir = os.path.join(self.output_dir, "screenshots")
        os.makedirs(screenshots_output_dir, exist_ok=True)
        for root, _, files in os.walk(self.screenshots_dir):
            for file in files:
                if file.endswith(".png"):
                    src_path = os.path.join(root, file)
                    dest_path = os.path.join(screenshots_output_dir, file)
                    if not os.path.exists(dest_path):
                        shutil.copyfile(src_path, dest_path)

    def find_screenshot_and_copy(self, test_name):
        screenshots_output_dir = os.path.join(self.output_dir, "screenshots")
        os.makedirs(screenshots_output_dir, exist_ok=True)

        # We'll look for any .png file where test_name is contained in the filename (partial match)
        for root, _, files in os.walk(self.screenshots_dir):
            for file in files:
                if file.endswith(".png") and test_name in file:
                    src_path = os.path.join(root, file)

                    dest_path = os.path.join(screenshots_output_dir, file)

                    shutil.copyfile(src_path, dest_path)

                    # Return relative path from output_dir for HTML src
                    return os.path.join("screenshots", file)
        return None

    def format_error_with_diffs(self, error_text: str) -> str:
        if not error_text:
            return ""

        lines = html.escape(error_text).splitlines()
        html_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("-"):
                html_lines.append(
                    f"<div style='color: red; background-color: #ffecec; padding: 2px; border-left: 4px solid red;'>❌ {line}</div>"
                )
            elif stripped.startswith("+"):
                html_lines.append(
                    f"<div style='color: green; background-color: #eaffea; padding: 2px; border-left: 4px solid green;'>✅ {line}</div>"
                )
            elif stripped.startswith("E "):
                html_lines.append(
                    f"<div style='color: #d8000c; background-color: #fff2f2; padding: 2px; border-left: 4px solid #d8000c;'>{line}</div>"
                )
            elif "AssertionError" in stripped:
                html_lines.append(
                    f"<div style='color: darkorange; font-weight: bold; padding: 2px;'>{line}</div>"
                )
            else:
                html_lines.append(
                    f"<pre style='margin: 0; font-family: monospace;'>{line}</pre>"
                )
        return "\n".join(html_lines)

    def generate_html_report(self):
        # Extract all unique markers
        ignore_markers = {"link"}
        all_markers = set()
        for test in self.results:
            for marker in test.get("markers", []):
                if marker not in ignore_markers:
                    all_markers.add(marker)

        html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      body {{ font-family: Arial, sans-serif; padding: 1rem; background: #f9f9f9; }}
      .test {{ border: 1px solid #ddd; margin-bottom: 0.5rem; border-radius: 5px; background: white; }}
      .header {{ padding: 0.5rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }}
      .header.passed {{ background: #e6f4ea; color: #2f7a33; }}
      .header.failed {{ background: #fdecea; color: #a83232; }}
      .header.skipped {{  background: #fff8e1; color: #b36b00;  }}
      .header.error {{  background: #f0f0f0; color: #f0f0f0;  }}
      .details {{ padding: 0.5rem 1rem; display: none; border-top: 1px solid #ddd; }}
      .toggle::before {{ content: "▶"; display: inline-block; margin-right: 0.5rem; transition: transform 0.3s ease; }}
      .header.expanded .toggle::before {{ transform: rotate(90deg); }}
      .checkbox-container {{ margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }}
      .details-content {{ display: flex; gap: 1rem; align-items: flex-start; }}
      .details-text {{ flex: 1; min-width: 0; }}
      .details-screenshot {{ flex-shrink: 0; margin: 1rem; box-shadow: 0 0 10px 0 rgba(0, 0, 0, 0.1); }}
      .details-screenshot img {{width: 300px; height: 200px; object-fit: contain; border: 1px solid #ccc; border-radius: 3px; background: #f8f8f8; cursor: pointer; transition: transform 0.2s ease; transform: scale(1.05); }}
      .details-screenshot img:hover {{  transform: scale(1.05); }}
      
      /* Mobile and tablet responsiveness */
      @media (max-width: 768px) {{
        .header {{ flex-direction: column; align-items: stretch; gap: 0.5rem; }}
        .header-section {{ justify-content: space-between; }}
        .test-info {{ min-width: auto; }}
        .meta {{ flex-direction: column; gap: 0.25rem; }}
        .badges-and-timing {{ justify-content: flex-start; flex-wrap: wrap; }}
        .badges-and-timing > * {{ margin-left: 0; margin-right: 0.5rem; }}
        
        .details-content {{ flex-direction: column; gap: 0.5rem; }}
        .details-screenshot {{ align-self: center; }}
        .details-screenshot img {{ width: 100%; max-width: 300px; height: auto; min-height: 150px; }}
      }}
      
      @media (max-width: 480px) {{
        .header {{ padding: 0.75rem 0.5rem; }}
        .details {{ padding: 0.5rem; }}
        .test-info strong {{ font-size: 0.9rem; }}
        .nodeid-badge code {{ font-size: 0.5em; }}
        .worker-id {{ font-size: 0.75em; }}
        .timestamp {{ font-size: 0.85em; }}
        
        .details-screenshot img {{ max-width: 100%; height: auto; min-height: 120px; }}
        
        .checkbox-container {{ flex-direction: column; gap: 0.5rem; }}
        .checkbox-container label {{ margin-left: 0 !important; }}
      }}
      .details-screenshot img.fullscreen {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(1); width: auto; height: auto; max-width: 90vw; max-height: 90vh; z-index: 1000; background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.5); border-radius: 8px; }}
      .fullscreen-overlay {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.8); z-index: 999; display: none; }}  
      .search-container {{ margin-bottom: 1rem; }}
      .search-container input {{ box-sizing: border-box; }}
      .header-section {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
      .test-info {{ flex: 1; min-width: 200px; word-break: break-word; white-space: normal; }}
      .meta {{ justify-content: flex-start; flex: 1; word-break: break-word; white-space: normal; }}
      .badges-and-timing {{ justify-content: flex-end; flex-wrap: wrap; }}
      .timestamp {{ white-space: nowrap; font-weight: bold; }}
      .badges-and-timing > * {{ margin-left: 24px; }}
    </style>

    <script>
      function toggleDetails(headerElem) {{
        headerElem.classList.toggle('expanded');
        const details = headerElem.nextElementSibling;
        details.style.display = (details.style.display === 'block') ? 'none' : 'block';
      }}

      function copyToClipboard(text) {{
        navigator.clipboard.writeText(text).then(() => {{
          console.log("Copied: " + text);
        }}).catch((err) => {{
          console.error("Copy failed", err);
        }});
      }}

      function toggleFullscreen(img) {{
        const overlay = document.getElementById('fullscreen-overlay');
        if (img.classList.contains('fullscreen')) {{
          img.classList.remove('fullscreen');
          overlay.style.display = 'none';
          document.body.style.overflow = 'auto';
        }} else {{
          img.classList.add('fullscreen');
          overlay.style.display = 'block';
          document.body.style.overflow = 'hidden';
        }}
      }}

      function closeFullscreen() {{
        const fullscreenImg = document.querySelector('.details-screenshot img.fullscreen');
        const overlay = document.getElementById('fullscreen-overlay');
        
        if (fullscreenImg) {{
          fullscreenImg.classList.remove('fullscreen');
          overlay.style.display = 'none';
          document.body.style.overflow = 'auto';
        }}
      }}


      function toggleFilter(longestCheckbox) {{
        const failedCheckbox = document.getElementById('failedOnlyCheckbox');
        const skippedCheckbox = document.getElementById('skippedOnlyCheckbox');
        const untrackedCheckbox = document.getElementById('untrackedOnlyCheckbox');
        const flakyCheckbox = document.getElementById('flakyOnlyCheckbox');
        const testsContainer = document.getElementById('tests-container');
        const testElements = Array.from(testsContainer.querySelectorAll('.test'));

        if (longestCheckbox.checked) {{
          failedCheckbox.checked = false;
          skippedCheckbox.checked = false;
          untrackedCheckbox.checked = false;
          flakyCheckbox.checked = false;
          // Re-enable all tests before sorting
          testElements.forEach(el => el.style.display = 'block');

          // Sort and reorder
          testElements.sort((a, b) => {{
            const aDuration = parseFloat(
        a.querySelector('.timestamp').textContent.replace(/[^\d.]/g, '')
        ) || 0;
            const bDuration = parseFloat(b.querySelector('.timestamp').textContent.replace(/[^\d.]/g, '')) || 0;
            return bDuration - aDuration;
          }});

          testElements.forEach(el => testsContainer.appendChild(el));
        }}

        // Reapply marker filter (should now handle failed/skipped too)
        filterByMarkers();
      }}

      function toggleUntrackedOnly(checkbox) {{
        const testCards = document.querySelectorAll('.test-card');
        const longestCheckbox = document.getElementById('longestOnlyCheckbox');
        const skippedCheckbox = document.getElementById('skippedOnlyCheckbox');
        const failedCheckbox = document.getElementById('failedOnlyCheckbox');
        const flakyCheckbox = document.getElementById('flakyOnlyCheckbox');

        if (checkbox.checked) {{
          longestCheckbox.checked = false;
          skippedCheckbox.checked = false;
          failedCheckbox.checked = false;
          flakyCheckbox.checked = false
          testCards.forEach(card => {{
            const hasLink = card.querySelector('a[href]');
            card.style.display = hasLink ? 'none' : 'block';
          }});
        }} else {{
          testCards.forEach(card => {{
            card.style.display = 'block';
          }});
        }}
      }}

      function toggleUntrackedInfo() {{
        const card = document.getElementById('untrackedInfoCard');
        card.style.display = card.style.display === 'none' ? 'block' : 'none';
      }}

      function toggleFlakyOnly(checkbox) {{
          const longestCheckbox = document.getElementById('longestOnlyCheckbox');
          const untrackedCheckbox = document.getElementById('untrackedOnlyCheckbox');
          const skippedCheckbox = document.getElementById('skippedOnlyCheckbox');
          const failedCheckbox = document.getElementById('failedOnlyCheckbox');
        const testElements = document.querySelectorAll('.test');
        if (checkbox.checked) {{
          longestCheckbox.checked = false;
          skippedCheckbox.checked = false;
          failedCheckbox.checked = false;
          untrackedCheckbox.checked = false;
          testElements.forEach(el => {{
            const isFlaky = el.querySelector('.is-flaky') !== null;
            el.style.display = isFlaky ? 'block' : 'none';
          }});
        }} else {{
          testElements.forEach(el => {{
            el.style.display = 'block';
          }});
        }}
      }}

      function toggleFailedOnly(failedCheckbox) {{
        const longestCheckbox = document.getElementById('longestOnlyCheckbox');
        const untrackedCheckbox = document.getElementById('untrackedOnlyCheckbox');
        const skippedCheckbox = document.getElementById('skippedOnlyCheckbox');
        const flakyCheckbox = document.getElementById('flakyOnlyCheckbox');
        const testElements = document.querySelectorAll('.test');
        if (failedCheckbox.checked) {{
          longestCheckbox.checked = false;
          untrackedCheckbox.checked = false;
          skippedCheckbox.checked = false;
          flakyCheckbox.checked = false;
          testElements.forEach(el => {{
            const header = el.querySelector('.header');
            const isFailed = header.classList.contains('failed');
            el.style.display = isFailed ? 'block' : 'none';
          }});
        }} else {{
          testElements.forEach(el => el.style.display = 'block');
        }}
        filterByMarkers(); // Reapply marker filter
      }}

      function toggleSkippedOnly(skippedCheckbox) {{
        const longestCheckbox = document.getElementById('longestOnlyCheckbox');
        const failedCheckbox = document.getElementById('failedOnlyCheckbox');
        const untrackedCheckbox = document.getElementById('untrackedOnlyCheckbox');
        const flakyCheckbox = document.getElementById('flakyOnlyCheckbox');
        const testElements = document.querySelectorAll('.test');

        if (skippedCheckbox.checked) {{
          longestCheckbox.checked = false;
          failedCheckbox.checked = false;
          untrackedCheckbox.checked = false;
          flakyCheckbox.checked = false;
          testElements.forEach(el => {{
            const header = el.querySelector('.header');
            const isSkipped = header.classList.contains('skipped');
            el.style.display = isSkipped ? 'block' : 'none';
          }});
        }} else {{
          testElements.forEach(el => el.style.display = 'block');
        }}

        filterByMarkers(); // Reapply marker filter
      }}

      function initializeUniversalSearch() {{
          const searchInput = document.getElementById('universal-search');
          if (!searchInput) return;

          searchInput.addEventListener('input', function (e) {{
              const filter = e.target.value.toLowerCase();
              document.querySelectorAll('.test-card').forEach(card => {{
                  const name = card.getAttribute('data-name') || '';
                  const link = card.getAttribute('data-link') || '';
                  const isVisible = name.toLowerCase().includes(filter) || link.toLowerCase().includes(filter);
                  card.style.display = isVisible ? '' : 'none';
              }});
          }});
        }}

      document.addEventListener('DOMContentLoaded', initializeUniversalSearch);

      function filterByMarkers() {{
        const selected = Array.from(document.querySelectorAll('.marker-filter input[type="checkbox"]:checked')).map(cb => cb.value);
        const failedOnly = document.getElementById('failedOnlyCheckbox').checked;
        const skippedOnly = document.getElementById('skippedOnlyCheckbox').checked;

        document.querySelectorAll('.test').forEach(el => {{
          const header = el.querySelector('.header');
          const markers = el.getAttribute('data-markers').split(',');
          const isFailed = header.classList.contains('failed');
          const isSkipped = header.classList.contains('skipped');

          const showAllMarkers = selected.length === 0;
          const matchesMarker = showAllMarkers || selected.some(m => markers.includes(m));
          const matchesFailed = !failedOnly || isFailed;
          const matchesSkipped = !skippedOnly || isSkipped;

          el.style.display = (matchesMarker && matchesFailed && matchesSkipped) ? 'block' : 'none';
        }});
      }}


      window.onload = function() {{
        const failedCheckbox = document.getElementById('failedOnlyCheckbox');
        const longestCheckbox = document.getElementById('longestOnlyCheckbox');
        const skippedCheckbox = document.getElementById('skippedOnlyCheckbox');
        const untrackedCheckbox = document.getElementById('untrackedOnlyCheckbox');
        const flakyCheckbox = document.getElementById('flakyOnlyCheckbox');
        failedCheckbox.checked = true;
        toggleFailedOnly(failedCheckbox);
        failedCheckbox.addEventListener('change', () => toggleFailedOnly(failedCheckbox));
        longestCheckbox.addEventListener('change', () => toggleFilter(longestCheckbox));
        skippedCheckbox.addEventListener('change', () => toggleSkippedOnly(skippedCheckbox));
        untrackedCheckbox.addEventListener('change', () => toggleUntrackedOnly(untrackedCheckbox));
        flakyCheckbox.addEventListener('change', () => toggleFlakyOnly(flakyCheckbox));
        const markerCheckboxes = document.querySelectorAll('.marker-filter input[type="checkbox"]');
        markerCheckboxes.forEach(cb => cb.addEventListener('change', filterByMarkers));
      }};
    </script>
    </head>
    <body>
    <div id="fullscreen-overlay" class="fullscreen-overlay" onclick="closeFullscreen()"></div>
    <div class="checkbox-container">
      <label>
        <input type="checkbox" id="failedOnlyCheckbox" />
        Show only failed tests
      </label>
      <label>
        <input type="checkbox" id="skippedOnlyCheckbox" />
        Show only skipped tests
      </label>
      <label style="margin-left: 1rem;">
        <input type="checkbox" id="longestOnlyCheckbox" />
        Sort by longest running tests
      </label>
      <label style="margin-left: 1rem;">
        <input type="checkbox" id="untrackedOnlyCheckbox" />
        Show untracked
      </label>
      <span onclick="toggleUntrackedInfo()" style="
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 18px;
  height: 18px;
  margin-left: 6px;
  background-color: #3498db;
  color: white;
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  user-select: none;
" title="What is untracked?">i</span>

<div id="untrackedInfoCard" style="
  display: none;
  background: #f9f9f9;
  color: #333;
  border: 1px solid #ccc;
  border-radius: 6px;
  padding: 10px 14px;
  margin-top: 8px;
  max-width: 400px;
  font-size: 0.85em;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
">
  <strong>Untracked Tests:</strong><br>
  These tests do not have any associated tracking markers like:
  <ul style="margin: 6px 0 0 16px; padding: 0;">
    <li><code>pytest.mark.link("https://...")</code></li>
    <li><code>pytest.mark.jira("PROJ-123")</code></li>
    <li><code>pytest.mark.issue("https://...")</code></li>
    <li><code>pytest.mark.testcase("https://...")</code></li>
  </ul>
  Add these markers to your test to track them better
</div>
<label style="margin-left: 1rem;">
  <input type="checkbox" id="flakyOnlyCheckbox">
  Show flaky tests only
</label>
    </div>
    <div class="search-container">
          <input
  type="text"
  id="universal-search"
  placeholder="🔍 Search by anything, testname? link ids?..."
  style="width: 100%; padding: 10px; margin-bottom: 20px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px;"
/>
    </div>


    <div id="markersFilter" class="marker-filter" style="margin-bottom: 1rem;">
      <strong>Filter by Markers:</strong><br/>
    """

        # Add checkboxes for all markers
        for marker in sorted(all_markers):
            html += f'<label><input type="checkbox" value="{marker}" /> {marker}</label> '

        html += '<div id="tests-container">'

        # Generate test blocks
        for test in self.results:
            status_class = (
                'passed' if test['status'] == 'passed' else
                'failed' if test['status'] == 'failed' else
                'skipped'
            )
            error_text = test.get("error", "")
            error_html = f"<pre>{self.format_error_with_diffs(error_text)}</pre>" if error_text else ""
            screenshot_path = self.find_screenshot_and_copy(test['test'])
            screenshot_html = f'<div class="details-screenshot"><img src="{screenshot_path}" alt="Screenshot" onclick="toggleFullscreen(this)"></div>' if screenshot_path else ""
            markers = test.get("markers")
            marker_str = ",".join(markers) if isinstance(markers, list) else ""
            stdout_html = ""
            if test.get('stdout'):
                stdout_html = f"<div><strong>STDOUT:</strong><pre>{test['stdout']}</pre></div>"

            stderr_html = ""
            if test.get('stderr'):
                stderr_html = f"<div><strong>STDERR:</strong><pre>{test['stderr']}</pre></div>"

            logs_html = ""
            if test.get('logs'):
                logs_html = f"<div><strong>Logs:</strong><pre>{test['logs']}</pre></div>"

            flaky_badge = ""
            if test.get("flaky"):
                flaky_badge = (
                    '<span class="is-flaky" '
                    'style="background:#f39c12;color:white;padding:2px 6px;'
                    'border-radius:3px;font-weight:bold;font-size:0.85em;">FLAKY</span>'
                )
            else:
                 # Invisible placeholder to preserve layout
                flaky_badge = '<span style="display:inline-block; min-width:40px;"></span>'

            link_html = ""
            links = test.get("links", [])
            if links:
                for url in links:
                    link_html += (
                        f'<a href="{url}" target="_blank" '
                        f'style="background:#3498db;color:white;padding:2px 6px;'
                        f'border-radius:3px;font-weight:bold;font-size:0.85em;'
                        f'text-decoration:none;margin-right:6px;"> Link </a>'
                    )
            else:
              # Invisible placeholder to preserve layout
              link_html = '<span style="display:inline-block; min-width:45px;"></span>'

            html += f'''
    
<div class="test test-card" data-name="{test['test']}" data-link="{','.join(test.get('links') or [])}" data-markers="{marker_str}">
  <div class="header {status_class}" onclick="toggleDetails(this)">
    <div class="header-section test-info">
      <span class="toggle"></span>
      <strong>{test["test"]}</strong>
      <span>— {test["status"].upper()}</span>
    </div>
    <div class="header-section meta">
      <span class="nodeid-badge" style="display: flex; align-items: center; gap: 6px;">
        <code style="font-size: 0.6em; color: #555;">{test["nodeid"]}</code>
        <button class="copy-btn"
                onclick="event.stopPropagation(); copyToClipboard('{test["nodeid"]}')"
                title="Copy full test path"
                style="
                  cursor: pointer;
                  background: none;
                  border: none;
                  font-size: 1.2em;
                  padding: 0;
                  line-height: 1;
                ">
          📋
        </button>
      </span>
      <span class="worker-id" style="background: #ddd; border-radius: 3px; padding: 2px 5px; font-size: 0.85em; font-weight: bold;">{test["worker"]}</span>
    </div>

    <div class="header-section badges-and-timing">
      {flaky_badge}
      {link_html}
      <span class="timestamp">⏱ {test.get("duration", 0):.2f}s</span>
    </div>
  </div>

  <div class="details">
    <div class="details-content">
      <div class="details-text">
        {error_html}
        {stdout_html}
        {stderr_html}
        {logs_html}
      </div>
      {screenshot_html}
    </div>
  </div>
</div>

    '''

        # Add summary
        total_tests = len(self.results)
        failed_tests = sum(1 for t in self.results if t['status'] == 'failed')
        error_tests = sum(1 for t in self.results if t['status'] == 'error')
        slowest_test = max(self.results, key=lambda x: x.get('duration', 0), default=None)
        slowest_test_name = slowest_test['test'] if slowest_test else 'N/A'
        slowest_test_duration = slowest_test.get('duration', 0) if slowest_test else 0

        summary_html = f"""
            <div style="padding: 1rem; background: {'#e6f4ea' if failed_tests == 0 and error_tests == 0 else '#fdecea'}; 
            border: 1px solid {'#2f7a33' if failed_tests == 0 and error_tests == 0 else '#a83232'}; 
            border-radius: 5px; margin-bottom: 1rem;">
              {'<strong>Bingo!</strong> All your tests passed!' if failed_tests == 0 and error_tests == 0 else
        f'Total tests: {total_tests}, Failures: {failed_tests}, Errors: {error_tests}.'}
              The slowest test was <strong>{slowest_test_name}</strong> at {slowest_test_duration:.2f}s.
            </div>
            """

        html = html.replace('<div id="tests-container">', summary_html + '<div id="tests-container">')
        html += "</div></body></html>"

        # Save report
        os.makedirs(self.output_dir, exist_ok=True)
        output_file = os.path.join(self.output_dir, "report.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

if __name__ == "__main__":
    main()
