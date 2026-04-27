import tempfile
import shutil
from pathlib import Path
import types
import sys
import re

tmp = tempfile.mkdtemp()

try:
    root = Path(tmp)

    # files that SHOULD be filtered out
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("bad")

    (root / ".github/workflows").mkdir(parents=True)
    (root / ".github/workflows/test.yml").write_text("bad")

    # files that SHOULD show up
    (root / "good.txt").write_text("ok")
    (root / "folder").mkdir()
    (root / "folder/file.py").write_text("ok")

    # load release_files.py
    test_module = types.ModuleType("test_script")

    with open("release_files.py") as f:
        code = f.read()

    test_module.__dict__["__file__"] = "release_files.py"
    exec(code, test_module.__dict__)

    # point release_files.py logic at fake temp root
    test_module.ROOT = tmp

    expected = {"good.txt", "folder/file.py"}
    actual = set()

    for f in Path(test_module.ROOT).rglob("*"):
        if not (f.is_file() or f.is_symlink()):
            continue

        # normalize Windows backslashes to forward slashes
        rf = str(f.relative_to(test_module.ROOT)).replace("\\", "/")

        blacklisted = any(re.search(p, rf) for p in test_module.blacklist)
        whitelisted = any(re.search(p, rf) for p in test_module.whitelist)

        if blacklisted and not whitelisted:
            continue

        actual.add(rf)

    print("---- OUTPUT ----")
    for f in sorted(actual):
        print(f)
    print("---- TEST DONE ----")

    if actual == expected:
        print("===== TEST_RELEASE_FILES PASSED =====")
    else:
        print("===== TEST_RELEASE_FILES FAILED =====")
        print("Expected:", expected)
        print("Actual:", actual)
        sys.exit(1)

finally:
    shutil.rmtree(tmp)