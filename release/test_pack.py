import sys
import types
import runpy
import io
from contextlib import redirect_stdout, redirect_stderr

fake_basedir = types.ModuleType("basedir")
fake_basedir.BASEDIR = "."

fake_common = types.ModuleType("common")
fake_common.basedir = fake_basedir

fake_openpilot = types.ModuleType("openpilot")
fake_openpilot.common = fake_common

sys.modules["openpilot"] = fake_openpilot
sys.modules["openpilot.common"] = fake_common
sys.modules["openpilot.common.basedir"] = fake_basedir

sys.argv = ["pack.py", "math"]

out = io.StringIO()
err = io.StringIO()

try:
  with redirect_stdout(out), redirect_stderr(err):
    runpy.run_path("pack.py", run_name="__main__")
except SystemExit:
  pass

output = out.getvalue() + err.getvalue()

if "does not have a main" in output:
  print("TEST PASSED: pack.py correctly handled module with no main()")
else:
  print("TEST FAILED: expected missing main() warning")
  print(output)
  sys.exit(1)