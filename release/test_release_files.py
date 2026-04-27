import os
import tempfile
import shutil
from pathlib import Path
import types

# ---- create fake directory structure ----
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

    # ---- load your script ----
    test_module = types.ModuleType("test_script")

    with open("release_files.py") as f:
        code = f.read()

    # FIX: define __file__ so script doesn't crash
    test_module.__dict__["__file__"] = "release_files.py"

    exec(code, test_module.__dict__)

    # override ROOT to temp dir
    test_module.ROOT = tmp

    print("---- OUTPUT ----")

    import re

    for f in Path(test_module.ROOT).rglob("**/*"):
        if not (f.is_file() or f.is_symlink()):
            continue

        rf = str(f.relative_to(test_module.ROOT))

        blacklisted = any(re.search(p, rf) for p in test_module.blacklist)
        whitelisted = any(re.search(p, rf) for p in test_module.whitelist)

        if blacklisted and not whitelisted:
            continue

        print(rf)

    print("---- TEST DONE ----")

finally:
    shutil.rmtree(tmp)