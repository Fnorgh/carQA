from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


CARD_PATH = Path(__file__).resolve().parents[2] / "card.py"
GREEN = "\033[92m"
RESET = "\033[0m"
CHECK = "\033[32m[PASS]\033[0m"


class EventName:
  buttonCancel = "buttonCancel"
  pcmEnable = "pcmEnable"
  pcmDisable = "pcmDisable"


class FakeCloudLog:
  def __init__(self):
    self.warnings: list[str] = []

  def warning(self, message: str):
    self.warnings.append(message)


class FakePubSocket:
  def __init__(self):
    self.sent = []

  def send(self, value):
    self.sent.append(value)


class FakeCanMessage:
  def __init__(self, address, dat, src):
    self.address = address
    self.dat = dat
    self.src = src


class FakeCanPacket:
  def __init__(self, *messages):
    self.can = list(messages)


class FakeParams:
  def __init__(self, initial: dict[str, bool] | None = None):
    self.values = dict(initial or {})
    self.calls: list[tuple[str, object, object]] = []

  def get_bool(self, key: str, block: bool = False):
    self.calls.append(("get_bool", key, block))
    return self.values.get(key, False)

  def remove(self, key: str):
    self.calls.append(("remove", key, None))
    self.values.pop(key, None)

  def put_bool(self, key: str, value: bool):
    self.calls.append(("put_bool", key, value))
    self.values[key] = value


# Stub modules
def _install_card_stub_modules(cloudlog_obj: FakeCloudLog) -> list[str]:
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
  cereal_msg = ModuleType("cereal.messaging")
  cereal_car.CarState = SimpleNamespace(new_message=lambda: SimpleNamespace())
  cereal_car.CarParams = SimpleNamespace(new_message=lambda: SimpleNamespace(), from_bytes=lambda *_args, **_kwargs: SimpleNamespace())
  cereal_car.CarControl = SimpleNamespace(new_message=lambda: SimpleNamespace())
  cereal_log.OnroadEvent = SimpleNamespace(EventName=EventName)
  cereal_msg.SubSocket = object
  cereal_msg.PubSocket = object
  cereal_msg.drain_sock = lambda logcan, wait_for_one=False: list(getattr(logcan, "packets", []))
  cereal_msg.drain_sock_raw = lambda logcan, wait_for_one=False: []
  cereal_msg.sub_sock = lambda *args, **kwargs: SimpleNamespace()
  cereal_msg.PubMaster = lambda *args, **kwargs: SimpleNamespace(sock={})
  cereal_msg.SubMaster = lambda *args, **kwargs: SimpleNamespace(
    update=lambda *_: None, all_alive=lambda *_: True, all_checks=lambda *_: True,
    frame=0, seen={}, __getitem__=lambda self, key: SimpleNamespace(enabled=False),
  )
  cereal_msg.new_message = lambda *args, **kwargs: SimpleNamespace()
  cereal_msg.recv_one_retry = lambda *args, **kwargs: SimpleNamespace(can=[])
  cereal_module.car = cereal_car
  cereal_module.log = cereal_log
  cereal_module.messaging = cereal_msg
  register("cereal", cereal_module)
  register("cereal.car", cereal_car)
  register("cereal.log", cereal_log)
  register("cereal.messaging", cereal_msg)

  opendbc_module = ModuleType("opendbc")
  opendbc_car = ModuleType("opendbc.car")
  opendbc_car.DT_CTRL = 0.01
  opendbc_car.structs = SimpleNamespace(
    CarControl=SimpleNamespace(Actuators=lambda: SimpleNamespace()),
    RadarDataT=SimpleNamespace,
  )
  register("opendbc", opendbc_module)
  register("opendbc.car", opendbc_car)

  can_definitions = ModuleType("opendbc.car.can_definitions")
  can_definitions.CanData = lambda address, dat, src: SimpleNamespace(address=address, dat=dat, src=src)
  can_definitions.CanRecvCallable = object
  can_definitions.CanSendCallable = object
  register("opendbc.car.can_definitions", can_definitions)

  carlog_module = ModuleType("opendbc.car.carlog")
  carlog_module.carlog = SimpleNamespace(addHandler=lambda *_: None)
  register("opendbc.car.carlog", carlog_module)

  fw_versions = ModuleType("opendbc.car.fw_versions")
  fw_versions.ObdCallback = object
  register("opendbc.car.fw_versions", fw_versions)

  car_helpers = ModuleType("opendbc.car.car_helpers")
  car_helpers.interfaces = {"FAKE": SimpleNamespace(RadarInterface=lambda cp: SimpleNamespace(update=lambda can_list: None))}
  car_helpers.get_car = lambda *args, **kwargs: SimpleNamespace(
    CP=SimpleNamespace(carFingerprint="FAKE"), CC=None, CS=SimpleNamespace()
  )
  register("opendbc.car.car_helpers", car_helpers)

  interfaces_module = ModuleType("opendbc.car.interfaces")
  interfaces_module.CarInterfaceBase = object
  interfaces_module.RadarInterfaceBase = object
  register("opendbc.car.interfaces", interfaces_module)

  openpilot_module = ModuleType("openpilot")
  openpilot_common = ModuleType("openpilot.common")
  openpilot_params = ModuleType("openpilot.common.params")
  openpilot_params.Params = FakeParams
  openpilot_realtime = ModuleType("openpilot.common.realtime")
  openpilot_realtime.config_realtime_process = lambda *args, **kwargs: None
  openpilot_realtime.Priority = SimpleNamespace(CTRL_HIGH=1)

  class Ratekeeper:
    def __init__(self, *args, **kwargs):
      self.remaining = 0.0

    def monitor_time(self):
      pass

  openpilot_realtime.Ratekeeper = Ratekeeper
  openpilot_swaglog = ModuleType("openpilot.common.swaglog")
  openpilot_swaglog.cloudlog = cloudlog_obj
  openpilot_swaglog.ForwardingHandler = lambda *_: object()

  openpilot_selfdrive = ModuleType("openpilot.selfdrive")
  openpilot_pandad = ModuleType("openpilot.selfdrive.pandad")
  openpilot_pandad.can_capnp_to_list = lambda can_strs: can_strs
  openpilot_pandad.can_list_to_can_capnp = lambda msgs, msgtype="sendcan", valid=True: {
    "msgs": msgs,
    "msgtype": msgtype,
    "valid": valid,
  }
  openpilot_car = ModuleType("openpilot.selfdrive.car")
  openpilot_cruise = ModuleType("openpilot.selfdrive.car.cruise")

  class DummyVCruiseHelper:
    def __init__(self, CP):
      self.v_cruise_kph = 0.0
      self.v_cruise_cluster_kph = 0.0

    def update_v_cruise(self, *args, **kwargs):
      pass

    def initialize_v_cruise(self, *args, **kwargs):
      pass

  openpilot_cruise.VCruiseHelper = DummyVCruiseHelper

  register("openpilot", openpilot_module)
  register("openpilot.common", openpilot_common)
  register("openpilot.common.params", openpilot_params)
  register("openpilot.common.realtime", openpilot_realtime)
  register("openpilot.common.swaglog", openpilot_swaglog)
  register("openpilot.selfdrive", openpilot_selfdrive)
  register("openpilot.selfdrive.pandad", openpilot_pandad)
  register("openpilot.selfdrive.car", openpilot_car)
  register("openpilot.selfdrive.car.cruise", openpilot_cruise)

  return stub_names


def _remove_stub_modules(names: list[str]):
  for name in names:
    sys.modules.pop(name, None)


# Module loader
def load_card_module(cloudlog_obj: FakeCloudLog):
  module_name = "softwareqa_card_under_test"
  if module_name in sys.modules:
    return sys.modules[module_name]

  stub_names = _install_card_stub_modules(cloudlog_obj)
  try:
    spec = importlib.util.spec_from_file_location(module_name, CARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
  finally:
    _remove_stub_modules(stub_names)


# Card tests

def test_card_obd_callback_updates_only_on_change():
  cloudlog_obj = FakeCloudLog()
  card = load_card_module(cloudlog_obj)
  params = FakeParams({"ObdMultiplexingEnabled": False})

  callback = card.obd_callback(params)
  callback(True)

  assert ("remove", "ObdMultiplexingChanged", None) in params.calls
  assert ("put_bool", "ObdMultiplexingEnabled", True) in params.calls
  assert any(call[0] == "get_bool" and call[1] == "ObdMultiplexingChanged" and call[2] is True for call in params.calls)
  assert cloudlog_obj.warnings == ["Setting OBD multiplexing to True", "OBD multiplexing set successfully"]


# Test runner

def run_case(number: int, title: str, case_fn):
  print(f"\n{GREEN}Test {number}: {title}{RESET}")
  case_fn()
  print(f"{CHECK} Test {number} passed")


def run_all_tests():
  cases = [
    (1, "obd_callback updates params only on change", test_card_obd_callback_updates_only_on_change),
  ]

  for number, title, case_fn in cases:
    run_case(number, title, case_fn)

  print(f"\n{GREEN}All card tests passed{RESET}")


if __name__ == "__main__":
  run_all_tests()
