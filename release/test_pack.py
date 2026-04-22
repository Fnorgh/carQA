import sys
import types
import runpy

# ---- fake the missing openpilot dependency ----
fake_basedir = types.ModuleType("basedir")
fake_basedir.BASEDIR = "."

fake_common = types.ModuleType("common")
fake_common.basedir = fake_basedir

fake_openpilot = types.ModuleType("openpilot")
fake_openpilot.common = fake_common

sys.modules["openpilot"] = fake_openpilot
sys.modules["openpilot.common"] = fake_common
sys.modules["openpilot.common.basedir"] = fake_basedir

# ---- fake CLI args ----
sys.argv = ["pack.py", "math"]  # safe built-in module

# ---- run the script ----
try:
    runpy.run_path("pack.py", run_name="__main__")
    print("TEST PASSED: script ran")
except Exception as e:
    print("TEST FAILED:", e)