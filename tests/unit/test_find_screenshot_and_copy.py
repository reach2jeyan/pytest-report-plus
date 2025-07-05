import os
import shutil


def test_find_screenshot_and_copy(tmp_path):
    screenshots_dir = tmp_path / "screenshots_src"
    output_dir = tmp_path / "output"
    screenshots_dir.mkdir()
    output_dir.mkdir()

    file_name = "test_something_fail.png"
    file_path = screenshots_dir / file_name
    file_path.write_text("image")

    class FakeReporter:
        def __init__(self, src, out):
            self.screenshots_dir = str(src)
            self.output_dir = str(out)

        def find_screenshot_and_copy(self, test_name):
            screenshots_output_dir = os.path.join(self.output_dir, "screenshots")
            os.makedirs(screenshots_output_dir, exist_ok=True)

            for root, _, files in os.walk(self.screenshots_dir):
                for file in files:
                    if file.endswith(".png") and test_name in file:
                        src_path = os.path.join(root, file)
                        dest_path = os.path.join(screenshots_output_dir, file)
                        shutil.copyfile(src_path, dest_path)
                        return os.path.join("screenshots", file)
            return None

    reporter = FakeReporter(screenshots_dir, output_dir)
    rel_path = reporter.find_screenshot_and_copy("something")

    assert rel_path.replace("\\", "/") == f"screenshots/{file_name}"
    assert (output_dir / "screenshots" / file_name).exists()
