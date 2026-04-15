import os

SCRIPT_PATH = "../../docs.py"

def read_file():
    with open(SCRIPT_PATH, "r") as f:
        return f.read()

# Test that the target script file actually exists
def test_file_exists():
    assert os.path.exists(SCRIPT_PATH)

# Test that the script has a proper entry point (main block)
def test_has_main_block():
    content = read_file()
    assert 'if __name__ == "__main__":' in content

# Test that basic required Python libraries are imported
def test_required_imports():
    content = read_file()
    assert "import argparse" in content
    assert "import os" in content

# Test that OpenPilot-specific imports are present
def test_openpilot_imports_present():
    content = read_file()
    assert "openpilot.common.basedir" in content
    assert "opendbc.car.docs" in content

# Test that the script uses the expected helper functions
def test_functions_used():
    content = read_file()
    assert "get_all_car_docs" in content
    assert "generate_cars_md" in content

# Test that an argument parser is defined for CLI usage
def test_argument_parser_defined():
    content = read_file()
    assert "ArgumentParser" in content

# Test that expected command-line arguments are supported
def test_cli_arguments_exist():
    content = read_file()
    assert "--template" in content
    assert "--out" in content

# Test that important output/template constants are defined
def test_constants_exist():
    content = read_file()
    assert "CARS_MD_OUT" in content
    assert "CARS_MD_TEMPLATE" in content

# simple test runner
if __name__ == "__main__":
    tests = [
        test_file_exists,
        test_has_main_block,
        test_required_imports,
        test_openpilot_imports_present,
        test_functions_used,
        test_argument_parser_defined,
        test_cli_arguments_exist,
        test_constants_exist,
    ]

    passed = 0

    for test in tests:
        try:
            test()
            print(f"{test.__name__}: PASS")
            passed += 1
        except AssertionError:
            print(f"{test.__name__}: FAIL")
        except Exception as e:
            print(f"{test.__name__}: ERROR ({e})")

    print(f"\n{passed}/{len(tests)} tests passed")