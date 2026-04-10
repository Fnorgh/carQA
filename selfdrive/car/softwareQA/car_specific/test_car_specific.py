from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


CAR_SPECIFIC_PATH = Path(__file__).resolve().parents[2] / "car_specific.py"
GREEN = "\033[92m"
RESET = "\033[0m"
CHECK = "\033[32m[PASS]\033[0m"


class EventList:
  def __init__(self):
    self._names: list[str] = []

  @property
  def names(self) -> list[str]:
    return self._names

  def add(self, event_name):
    self._names.append(event_name)


class ButtonType:
  cancel = "cancel"
  accelCruise = "accelCruise"
  decelCruise = "decelCruise"
  resumeCruise = "resumeCruise"
  setCruise = "setCruise"


class GearShifter:
  drive = "drive"
  reverse = "reverse"
  neutral = "neutral"


class NetworkLocation:
  fwdCamera = "fwdCamera"


class RawEnumValue:
  def __init__(self, raw):
    self._raw = raw

  @property
  def raw(self):
    return self

  def __repr__(self):
    return f"RawEnumValue({self._raw})"


class ButtonEvent:
  Type = ButtonType

  def __init__(self, type, pressed):
    self.type = type
    self.pressed = pressed


class StructsCarState:
  ButtonEvent = ButtonEvent
  GearShifter = GearShifter


class StructsCarParams:
  NetworkLocation = NetworkLocation


class ToyotaFlags:
  HYBRID = SimpleNamespace(value=1)


class EventName:
  belowEngageSpeed = "belowEngageSpeed"
  belowSteerSpeed = "belowSteerSpeed"
  buttonCancel = "buttonCancel"
  buttonEnable = "buttonEnable"
  doorOpen = "doorOpen"
  espDisabled = "espDisabled"
  espActive = "espActive"
  gasPressedOverride = "gasPressedOverride"
  manualRestart = "manualRestart"
  pcmDisable = "pcmDisable"
  pcmEnable = "pcmEnable"
  parkBrake = "parkBrake"
  preEnableStandstill = "preEnableStandstill"
  reverseGear = "reverseGear"
  resumeRequired = "resumeRequired"
  seatbeltNotLatched = "seatbeltNotLatched"
  speedTooHigh = "speedTooHigh"
  speedTooLow = "speedTooLow"
  steerDisengage = "steerDisengage"
  steerOverride = "steerOverride"
  steerTempUnavailable = "steerTempUnavailable"
  steerTempUnavailableSilent = "steerTempUnavailableSilent"
  steerUnavailable = "steerUnavailable"
  stockAeb = "stockAeb"
  stockFcw = "stockFcw"
  stockLkas = "stockLkas"
  vehicleSensorsInvalid = "vehicleSensorsInvalid"
  wrongCarMode = "wrongCarMode"
  wrongCruiseMode = "wrongCruiseMode"
  wrongGear = "wrongGear"
  cruiseDisabled = "cruiseDisabled"
  invalidLkasSetting = "invalidLkasSetting"
  accFaulted = "accFaulted"
  brakeHold = "brakeHold"


# Stub modules
def _install_stub_modules() -> list[str]:
  original_modules = {}
  stub_names = []

  def register(name: str, module: ModuleType):
    if name not in original_modules:
      original_modules[name] = sys.modules.get(name)
      stub_names.append(name)
    sys.modules[name] = module

  cereal_module = ModuleType("cereal")
  cereal_car = ModuleType("cereal.car")
  cereal_log = ModuleType("cereal.log")
  cereal_car.CarState = SimpleNamespace(ButtonEvent=ButtonEvent, GearShifter=GearShifter)
  cereal_car.CarControl = SimpleNamespace()
  cereal_log.OnroadEvent = SimpleNamespace(EventName=EventName)
  cereal_module.car = cereal_car
  cereal_module.log = cereal_log
  register("cereal", cereal_module)
  register("cereal.car", cereal_car)
  register("cereal.log", cereal_log)

  opendbc_module = ModuleType("opendbc")
  opendbc_car = ModuleType("opendbc.car")
  opendbc_car.DT_CTRL = 0.01
  opendbc_car.structs = SimpleNamespace(CarState=StructsCarState, CarParams=StructsCarParams)
  register("opendbc", opendbc_module)
  register("opendbc.car", opendbc_car)

  car_helpers = ModuleType("opendbc.car.car_helpers")
  car_helpers.interfaces = {
    "FAKE": SimpleNamespace(DRIVABLE_GEARS=[GearShifter.drive]),
    "FAKE2": SimpleNamespace(DRIVABLE_GEARS=[GearShifter.drive]),
  }
  register("opendbc.car.car_helpers", car_helpers)

  interfaces_module = ModuleType("opendbc.car.interfaces")
  interfaces_module.MAX_CTRL_SPEED = 55.0
  register("opendbc.car.interfaces", interfaces_module)

  toyota_values = ModuleType("opendbc.car.toyota.values")
  toyota_values.ToyotaFlags = ToyotaFlags
  register("opendbc.car.toyota.values", toyota_values)

  toyota_module = ModuleType("opendbc.car.toyota")
  register("opendbc.car.toyota", toyota_module)

  openpilot_module = ModuleType("openpilot")
  openpilot_selfdrive = ModuleType("openpilot.selfdrive")
  openpilot_selfdrived = ModuleType("openpilot.selfdrive.selfdrived")
  openpilot_events = ModuleType("openpilot.selfdrive.selfdrived.events")
  openpilot_events.Events = EventList
  register("openpilot", openpilot_module)
  register("openpilot.selfdrive", openpilot_selfdrive)
  register("openpilot.selfdrive.selfdrived", openpilot_selfdrived)
  register("openpilot.selfdrive.selfdrived.events", openpilot_events)

  return stub_names


def _remove_stub_modules(names: list[str]):
  for name in names:
    sys.modules.pop(name, None)


# Module loader
def load_car_specific_module():
  module_name = "softwareqa_car_specific_under_test"
  if module_name in sys.modules:
    return sys.modules[module_name]

  stub_names = _install_stub_modules()
  try:
    spec = importlib.util.spec_from_file_location(module_name, CAR_SPECIFIC_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
  finally:
    _remove_stub_modules(stub_names)


def make_car_params(**overrides):
  params = SimpleNamespace(
    brand="honda",
    carFingerprint="FAKE",
    pcmCruise=False,
    minEnableSpeed=10.0,
    minSteerSpeed=0.0,
    openpilotLongitudinalControl=False,
    flags=0,
    networkLocation=NetworkLocation.fwdCamera,
  )
  for key, value in overrides.items():
    setattr(params, key, value)
  return params


def make_car_state(**overrides):
  state = SimpleNamespace(
    vEgo=0.0,
    doorOpen=False,
    seatbeltUnlatched=False,
    gearShifter=GearShifter.drive,
    cruiseState=SimpleNamespace(available=True, enabled=False, standstill=False, nonAdaptive=False),
    espDisabled=False,
    espActive=False,
    stockFcw=False,
    stockAeb=False,
    stockLkas=False,
    brakeHoldActive=False,
    parkingBrake=False,
    accFaulted=False,
    steeringPressed=False,
    steeringDisengage=False,
    brakePressed=False,
    standstill=False,
    gasPressed=False,
    vehicleSensorsInvalid=False,
    invalidLkasSetting=False,
    lowSpeedAlert=False,
    buttonEnable=False,
    buttonEvents=[],
    steerFaultTemporary=False,
    steerFaultPermanent=False,
    steerOverride=False,
    blockPcmEnable=False,
    brake=0.0,
  )
  for key, value in overrides.items():
    setattr(state, key, value)
  return state


def make_control(**overrides):
  control = SimpleNamespace(
    actuators=SimpleNamespace(accel=0.0),
    cruiseControl=SimpleNamespace(resume=False),
    enabled=False,
  )
  for key, value in overrides.items():
    setattr(control, key, value)
  return control


# Honda tests

def test_honda_pcm_enable_and_low_speed_events():
  car_specific = load_car_specific_module()

  events = car_specific.CarSpecificEvents(make_car_params(brand="honda", pcmCruise=True)).update(
    make_car_state(vEgo=5.0, cruiseState=SimpleNamespace(available=True, enabled=True, standstill=False, nonAdaptive=False)),
    make_car_state(cruiseState=SimpleNamespace(available=True, enabled=False, standstill=False, nonAdaptive=False)),
    make_control(actuators=SimpleNamespace(accel=0.0)),
  )

  assert EventName.belowEngageSpeed in events.names
  assert EventName.pcmEnable in events.names


def test_honda_cruise_disabled_above_min_speed():
  car_specific = load_car_specific_module()

  events = car_specific.CarSpecificEvents(make_car_params(brand="honda", pcmCruise=True)).update(
    make_car_state(vEgo=20.0, cruiseState=SimpleNamespace(available=True, enabled=False, standstill=False, nonAdaptive=False)),
    make_car_state(cruiseState=SimpleNamespace(available=True, enabled=True, standstill=False, nonAdaptive=False)),
    make_control(actuators=SimpleNamespace(accel=0.0)),
  )

  assert EventName.cruiseDisabled in events.names
  assert EventName.speedTooLow not in events.names


# Chrysler tests

def test_chrysler_low_speed_alert_hysteresis():
  car_specific = load_car_specific_module()
  cp = make_car_params(brand="chrysler", minSteerSpeed=10.0)
  tester = car_specific.CarSpecificEvents(cp)

  low_events = tester.update(make_car_state(vEgo=10.25), make_car_state(vEgo=11.0), make_control())
  high_events = tester.update(make_car_state(vEgo=11.5), make_car_state(vEgo=10.25), make_control())

  assert EventName.belowSteerSpeed in low_events.names
  assert EventName.belowSteerSpeed not in high_events.names


# Toyota tests

def test_toyota_resume_required_and_manual_restart():
  car_specific = load_car_specific_module()

  events = car_specific.CarSpecificEvents(
    make_car_params(brand="toyota", openpilotLongitudinalControl=True, flags=ToyotaFlags.HYBRID.value)
  ).update(
    make_car_state(vEgo=0.0, standstill=True, brakePressed=False,
                   cruiseState=SimpleNamespace(available=True, enabled=False, standstill=True, nonAdaptive=False)),
    make_car_state(cruiseState=SimpleNamespace(available=True, enabled=False, standstill=False, nonAdaptive=False)),
    make_control(actuators=SimpleNamespace(accel=0.4), cruiseControl=SimpleNamespace(resume=False)),
  )

  assert EventName.resumeRequired in events.names
  assert EventName.belowEngageSpeed in events.names
  assert EventName.speedTooLow in events.names
  assert EventName.manualRestart in events.names


# GM tests

def test_gm_allows_enable_at_standstill_with_brake():
  car_specific = load_car_specific_module()

  events = car_specific.CarSpecificEvents(
    make_car_params(brand="gm", openpilotLongitudinalControl=True)
  ).update(
    make_car_state(vEgo=0.0, standstill=True, brake=20.0,
                   cruiseState=SimpleNamespace(available=True, enabled=False, standstill=False, nonAdaptive=False)),
    make_car_state(cruiseState=SimpleNamespace(available=True, enabled=False, standstill=False, nonAdaptive=False)),
    make_control(actuators=SimpleNamespace(accel=0.0)),
  )

  assert EventName.belowEngageSpeed not in events.names


# Common event tests

def test_common_events_for_driver_inputs():
  car_specific = load_car_specific_module()

  events = car_specific.CarSpecificEvents(make_car_params(brand="honda")).create_common_events(
    make_car_state(
      doorOpen=True,
      seatbeltUnlatched=True,
      steeringPressed=True,
      gasPressed=True,
      vEgo=60.0,
      buttonEvents=[ButtonEvent(ButtonType.cancel, True)],
    ),
    make_car_state(),
  )

  assert EventName.doorOpen in events.names
  assert EventName.seatbeltNotLatched in events.names
  assert EventName.steerOverride in events.names
  assert EventName.gasPressedOverride in events.names
  assert EventName.speedTooHigh in events.names
  assert EventName.buttonCancel in events.names


def test_steer_disengage_rising_edge_only():
  car_specific = load_car_specific_module()
  tester = car_specific.CarSpecificEvents(make_car_params(brand="honda"))

  rising_edge_events = tester.create_common_events(
    make_car_state(steeringDisengage=True),
    make_car_state(steeringDisengage=False),
  )
  sustained_events = tester.create_common_events(
    make_car_state(steeringDisengage=True),
    make_car_state(steeringDisengage=True),
  )

  assert EventName.steerDisengage in rising_edge_events.names
  assert EventName.steerDisengage not in sustained_events.names


def test_steer_fault_temp_silent_then_loud():
  car_specific = load_car_specific_module()
  tester = car_specific.CarSpecificEvents(make_car_params(brand="honda"))

  # Silent alert first
  silent_events = tester.create_common_events(
    make_car_state(steerFaultTemporary=True),
    make_car_state(),
  )

  # Force loud alert
  tester.create_common_events(make_car_state(steerFaultTemporary=False), make_car_state())
  tester.silent_steer_warning = False
  tester.steering_unpressed = 200

  loud_events = tester.create_common_events(
    make_car_state(steerFaultTemporary=True),
    make_car_state(),
  )

  assert EventName.steerTempUnavailableSilent in silent_events.names
  assert EventName.steerTempUnavailableSilent not in loud_events.names
  assert EventName.steerTempUnavailable in loud_events.names


def test_hyundai_cancel_button_blocked_with_pcm():
  car_specific = load_car_specific_module()

  events = car_specific.CarSpecificEvents(make_car_params(brand="hyundai", pcmCruise=True)).create_common_events(
    make_car_state(buttonEvents=[ButtonEvent(ButtonType.cancel, True)]),
    make_car_state(),
  )

  assert EventName.buttonCancel not in events.names


# Test runner

def run_case(number: int, title: str, case_fn):
  print(f"\n{GREEN}Test {number}: {title}{RESET}")
  case_fn()
  print(f"{CHECK} Test {number} passed")


def run_all_tests():
  cases = [
    (1, "honda: pcmEnable and belowEngageSpeed",          test_honda_pcm_enable_and_low_speed_events),
    (2, "honda: cruiseDisabled above minEnableSpeed+2",   test_honda_cruise_disabled_above_min_speed),
    (3, "chrysler: belowSteerSpeed hysteresis",           test_chrysler_low_speed_alert_hysteresis),
    (4, "toyota: resumeRequired and manualRestart",       test_toyota_resume_required_and_manual_restart),
    (5, "gm: standstill+brake exempts belowEngageSpeed",  test_gm_allows_enable_at_standstill_with_brake),
    (6, "common: driver input events",                    test_common_events_for_driver_inputs),
    (7, "common: steerDisengage on rising edge only",     test_steer_disengage_rising_edge_only),
    (8, "common: temp steer fault silent then loud",      test_steer_fault_temp_silent_then_loud),
    (9, "common: hyundai cancel button blocked with pcm", test_hyundai_cancel_button_blocked_with_pcm),
  ]

  for number, title, case_fn in cases:
    run_case(number, title, case_fn)

  print(f"\n{GREEN}All car_specific tests passed{RESET}")


if __name__ == "__main__":
  run_all_tests()
