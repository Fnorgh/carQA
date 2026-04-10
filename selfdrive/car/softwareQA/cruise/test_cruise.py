from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


CRUISE_PATH = Path(__file__).resolve().parents[2] / "cruise.py"
GREEN = "\033[92m"
RESET = "\033[0m"
CHECK = "\033[32m[PASS]\033[0m"


class RawEnumValue:
  def __init__(self, raw):
    self._raw = raw

  @property
  def raw(self):
    return self

  def __repr__(self):
    return f"RawEnumValue({self._raw})"


class CruiseButtonType:
  accelCruise = RawEnumValue("accelCruise")
  decelCruise = RawEnumValue("decelCruise")
  resumeCruise = RawEnumValue("resumeCruise")
  setCruise = RawEnumValue("setCruise")


# Stub modules
def _install_cruise_stub_modules() -> list[str]:
  original_modules = {}
  stub_names = []

  def register(name: str, module: ModuleType):
    if name not in original_modules:
      original_modules[name] = sys.modules.get(name)
      stub_names.append(name)
    sys.modules[name] = module

  cereal_module = ModuleType("cereal")
  cereal_car = ModuleType("cereal.car")
  cereal_car.CarState = SimpleNamespace(
    ButtonEvent=SimpleNamespace(Type=CruiseButtonType),
    new_message=lambda **kwargs: SimpleNamespace(**kwargs),
  )
  register("cereal", cereal_module)
  register("cereal.car", cereal_car)

  openpilot_module = ModuleType("openpilot")
  openpilot_common = ModuleType("openpilot.common")
  openpilot_constants = ModuleType("openpilot.common.constants")
  openpilot_constants.CV = SimpleNamespace(
    MPH_TO_KPH=1.609,
    MS_TO_KPH=3.6,
    KPH_TO_MS=1 / 3.6,
    MS_TO_MPH=2.23694,
  )
  register("openpilot", openpilot_module)
  register("openpilot.common", openpilot_common)
  register("openpilot.common.constants", openpilot_constants)

  return stub_names


def _remove_stub_modules(names: list[str]):
  for name in names:
    sys.modules.pop(name, None)


# Module loader
def load_cruise_module():
  module_name = "softwareqa_cruise_under_test"
  if module_name in sys.modules:
    return sys.modules[module_name]

  stub_names = _install_cruise_stub_modules()
  try:
    spec = importlib.util.spec_from_file_location(module_name, CRUISE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
  finally:
    _remove_stub_modules(stub_names)


def make_cruise_state(**overrides):
  state = SimpleNamespace(
    cruiseState=SimpleNamespace(available=True, speed=0.0, speedCluster=0.0, standstill=False),
    buttonEvents=[],
    gasPressed=False,
    vEgo=0.0,
  )
  for key, value in overrides.items():
    setattr(state, key, value)
  return state


def make_cruise_button_event(button_type, pressed):
  return SimpleNamespace(type=button_type, pressed=pressed)


# Init tests
def test_cruise_initializes_to_default_speed():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))

  helper.initialize_v_cruise(make_cruise_state(vEgo=0.0), experimental_mode=False)

  assert helper.v_cruise_initialized
  assert helper.v_cruise_kph == cruise.V_CRUISE_INITIAL
  assert helper.v_cruise_cluster_kph == cruise.V_CRUISE_INITIAL


def test_cruise_resume_button_restores_last_speed():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper.v_cruise_kph = 60.0       # Marks initialized
  helper.v_cruise_kph_last = 60.0

  helper.initialize_v_cruise(
    make_cruise_state(vEgo=15.0, buttonEvents=[make_cruise_button_event(cruise.ButtonType.resumeCruise, True)]),
    experimental_mode=False,
  )

  assert helper.v_cruise_kph == 60.0


# PCM tests

def test_cruise_pcm_speed_comes_from_car_state():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=True))

  helper.update_v_cruise(
    make_cruise_state(cruiseState=SimpleNamespace(available=True, speed=10.0, speedCluster=11.0, standstill=False)),
    enabled=True,
    is_metric=True,
  )

  assert helper.v_cruise_kph == 10.0 * 3.6
  assert helper.v_cruise_cluster_kph == 11.0 * 3.6


def test_cruise_pcm_unset_when_speed_zero():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=True))

  helper.update_v_cruise(
    make_cruise_state(cruiseState=SimpleNamespace(available=True, speed=0.0, speedCluster=0.0, standstill=False)),
    enabled=True,
    is_metric=True,
  )

  assert helper.v_cruise_kph == cruise.V_CRUISE_UNSET
  assert helper.v_cruise_cluster_kph == cruise.V_CRUISE_UNSET


def test_cruise_pcm_speed_minus_one_passthrough():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=True))

  helper.update_v_cruise(
    make_cruise_state(cruiseState=SimpleNamespace(available=True, speed=-1, speedCluster=-1, standstill=False)),
    enabled=True,
    is_metric=True,
  )

  assert helper.v_cruise_kph == -1
  assert helper.v_cruise_cluster_kph == -1


# Button logic tests

def test_cruise_unavailable_resets_to_unset():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper.v_cruise_kph = cruise.V_CRUISE_INITIAL
  helper.v_cruise_cluster_kph = cruise.V_CRUISE_INITIAL

  helper.update_v_cruise(
    make_cruise_state(cruiseState=SimpleNamespace(available=False, speed=0.0, speedCluster=0.0, standstill=False)),
    enabled=True,
    is_metric=True,
  )

  assert helper.v_cruise_kph == cruise.V_CRUISE_UNSET
  assert helper.v_cruise_cluster_kph == cruise.V_CRUISE_UNSET


def test_cruise_accel_increments_speed():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper.v_cruise_kph = cruise.V_CRUISE_INITIAL
  helper.button_change_states[cruise.ButtonType.accelCruise] = {"standstill": False, "enabled": True}

  helper.update_v_cruise(
    make_cruise_state(buttonEvents=[make_cruise_button_event(cruise.ButtonType.accelCruise, False)]),
    enabled=True,
    is_metric=True,
  )

  assert helper.v_cruise_kph == cruise.V_CRUISE_INITIAL + 1


def test_cruise_increment_on_decel_release():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper.v_cruise_kph = cruise.V_CRUISE_INITIAL
  helper.button_change_states[cruise.ButtonType.decelCruise] = {"standstill": False, "enabled": True}

  helper.update_v_cruise(
    make_cruise_state(buttonEvents=[make_cruise_button_event(cruise.ButtonType.decelCruise, False)]),
    enabled=True,
    is_metric=True,
  )

  assert helper.v_cruise_kph == cruise.V_CRUISE_INITIAL - 1


def test_cruise_accel_does_not_change_at_standstill():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper.v_cruise_kph = cruise.V_CRUISE_INITIAL
  helper.button_change_states[cruise.ButtonType.accelCruise] = {"standstill": True, "enabled": True}

  helper.update_v_cruise(
    make_cruise_state(
      cruiseState=SimpleNamespace(available=True, standstill=True, speed=0.0, speedCluster=0.0),
      buttonEvents=[make_cruise_button_event(cruise.ButtonType.accelCruise, False)],
    ),
    enabled=True,
    is_metric=True,
  )

  assert helper.v_cruise_kph == cruise.V_CRUISE_INITIAL


def test_cruise_speed_clamped_to_min_and_max():
  cruise = load_cruise_module()

  # Clamp minimum speed
  helper_min = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper_min.v_cruise_kph = cruise.V_CRUISE_MIN
  helper_min.button_change_states[cruise.ButtonType.decelCruise] = {"standstill": False, "enabled": True}
  helper_min.update_v_cruise(
    make_cruise_state(buttonEvents=[make_cruise_button_event(cruise.ButtonType.decelCruise, False)]),
    enabled=True,
    is_metric=True,
  )
  assert helper_min.v_cruise_kph == cruise.V_CRUISE_MIN

  # Clamp maximum speed
  helper_max = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper_max.v_cruise_kph = cruise.V_CRUISE_MAX
  helper_max.button_change_states[cruise.ButtonType.accelCruise] = {"standstill": False, "enabled": True}
  helper_max.update_v_cruise(
    make_cruise_state(buttonEvents=[make_cruise_button_event(cruise.ButtonType.accelCruise, False)]),
    enabled=True,
    is_metric=True,
  )
  assert helper_max.v_cruise_kph == cruise.V_CRUISE_MAX


def test_cruise_imperial_increment():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper.v_cruise_kph = cruise.V_CRUISE_INITIAL
  helper.button_change_states[cruise.ButtonType.decelCruise] = {"standstill": False, "enabled": True}

  helper.update_v_cruise(
    make_cruise_state(buttonEvents=[make_cruise_button_event(cruise.ButtonType.decelCruise, False)]),
    enabled=True,
    is_metric=False,
  )

  expected = cruise.V_CRUISE_INITIAL - cruise.IMPERIAL_INCREMENT
  assert abs(helper.v_cruise_kph - expected) < 0.01


def test_cruise_long_press_five_x_increment():
  cruise = load_cruise_module()
  helper = cruise.VCruiseHelper(SimpleNamespace(pcmCruise=False))
  helper.v_cruise_kph = cruise.V_CRUISE_INITIAL
  # Trigger long press
  helper.button_timers[cruise.ButtonType.accelCruise] = cruise.CRUISE_LONG_PRESS
  helper.button_change_states[cruise.ButtonType.accelCruise] = {"standstill": False, "enabled": True}

  helper.update_v_cruise(make_cruise_state(), enabled=True, is_metric=True)

  assert helper.v_cruise_kph == cruise.V_CRUISE_INITIAL + 5


# Test runner

def run_case(number: int, title: str, case_fn):
  print(f"\n{GREEN}Test {number}: {title}{RESET}")
  case_fn()
  print(f"{CHECK} Test {number} passed")


def run_all_tests():
  cases = [
    (1,  "initialize to default speed",                    test_cruise_initializes_to_default_speed),
    (2,  "resume button restores last speed",              test_cruise_resume_button_restores_last_speed),
    (3,  "pcm speed comes from car state",                 test_cruise_pcm_speed_comes_from_car_state),
    (4,  "pcm unset when speed is zero",                   test_cruise_pcm_unset_when_speed_zero),
    (5,  "pcm speed -1 passed through as -1",              test_cruise_pcm_speed_minus_one_passthrough),
    (6,  "unavailable cruise resets to V_CRUISE_UNSET",    test_cruise_unavailable_resets_to_unset),
    (7,  "accel button increments speed",                  test_cruise_accel_increments_speed),
    (8,  "decel release decrements speed",                 test_cruise_increment_on_decel_release),
    (9,  "accel does not change speed at standstill",      test_cruise_accel_does_not_change_at_standstill),
    (10, "speed clamped to V_CRUISE_MIN and V_CRUISE_MAX", test_cruise_speed_clamped_to_min_and_max),
    (11, "imperial increment used when is_metric=False",   test_cruise_imperial_increment),
    (12, "long press gives 5x increment",                  test_cruise_long_press_five_x_increment),
  ]

  for number, title, case_fn in cases:
    run_case(number, title, case_fn)

  print(f"\n{GREEN}All cruise tests passed{RESET}")


if __name__ == "__main__":
  run_all_tests()
