#!/bin/bash

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_ROOT/selfdrive/car/softwareQA" || { echo "softwareQA not found"; exit 1; }

# ---- docs ----

cd docs || { echo "docs not found"; exit 1; }
echo "===== Running: $(pwd)/test_docs.py ====="
chmod +x test_docs.py 2>/dev/null
python test_docs.py
cd ..

# ---- car_specific ----

cd car_specific || { echo "car_specific not found"; exit 1; }
echo "===== Running: $(pwd)/test_car_specific.py ====="
chmod +x test_car_specific.py 2>/dev/null
python test_car_specific.py
cd ..

# ---- card ----

cd card || { echo "card not found"; exit 1; }
echo "===== Running: $(pwd)/test_card.py ====="
chmod +x test_card.py 2>/dev/null
python test_card.py
cd ..

# ---- cruise ----

cd cruise || { echo "cruise not found"; exit 1; }
echo "===== Running: $(pwd)/test_cruise.py ====="
chmod +x test_cruise.py 2>/dev/null
python test_cruise.py
cd ..

# ---- cereal messaging tests ----
# skipped: has dependencies that can't really be run in the CI software-only workflow

# ---- release tests ----

cd "$REPO_ROOT/release" || { echo "release folder not found"; exit 1; }

echo "===== Running release tests in: $(pwd) ====="

for test in test_pack.py test_release_files.py
do
  echo "Running: $(pwd)/$test"
  chmod +x "$test" 2>/dev/null
  python "$test"
done

echo "===== All tests complete ====="
echo "Final dir: $(pwd)"