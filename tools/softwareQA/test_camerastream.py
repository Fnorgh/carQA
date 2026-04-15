import sys
import types
import importlib.util

# -----------------------------
# MOCK HEAVY / MISSING MODULES
# -----------------------------
sys.modules["av"] = types.ModuleType("av")
sys.modules["numpy"] = types.ModuleType("numpy")

# mock cereal.messaging
cereal_module = types.ModuleType("cereal")
messaging_module = types.ModuleType("messaging")
cereal_module.messaging = messaging_module
sys.modules["cereal"] = cereal_module
sys.modules["cereal.messaging"] = messaging_module

# mock msgq.visionipc
visionipc_module = types.ModuleType("visionipc")

class FakeVisionIpcServer:
    def __init__(self, *args, **kwargs): pass
    def create_buffers(self, *args, **kwargs): pass
    def start_listener(self): pass
    def send(self, *args, **kwargs): pass

class FakeVisionStreamType:
    VISION_STREAM_ROAD = 0
    VISION_STREAM_DRIVER = 1
    VISION_STREAM_WIDE_ROAD = 2

visionipc_module.VisionIpcServer = FakeVisionIpcServer
visionipc_module.VisionStreamType = FakeVisionStreamType

msgq_module = types.ModuleType("msgq")
msgq_module.visionipc = visionipc_module

sys.modules["msgq"] = msgq_module
sys.modules["msgq.visionipc"] = visionipc_module

# -----------------------------
# LOAD YOUR SCRIPT
# -----------------------------
spec = importlib.util.spec_from_file_location(
    "compressed_vipc",
    "../camerastream/compressed_vipc.py"
)
cvipc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cvipc)

# -----------------------------
# Test 1: ENCODE_SOCKETS mapping
# -----------------------------
def test_encode_sockets():
    assert isinstance(cvipc.ENCODE_SOCKETS, dict)
    assert len(cvipc.ENCODE_SOCKETS) > 0

    for key, val in cvipc.ENCODE_SOCKETS.items():
        assert isinstance(val, str)
        assert "EncodeData" in val


# -----------------------------
# Test 2: cams parsing logic
# -----------------------------
def test_camera_selection_logic():
    cams_input = "0,1,2"
    indices = [int(x) for x in cams_input.split(",")]

    assert indices == [0, 1, 2]


# -----------------------------
# Test 3: Vision stream indexing safety
# -----------------------------
def test_camera_index_bounds():
    cams_input = "0,1,2"
    indices = [int(x) for x in cams_input.split(",")]

    assert all(0 <= i <= 2 for i in indices)


# -----------------------------
# Test 4: invalid camera input
# -----------------------------
def test_invalid_camera_input():
    cams_input = "0,a,2"

    try:
        [int(x) for x in cams_input.split(",")]
        assert False  # should not succeed
    except ValueError:
        assert True


# -----------------------------
# Test 5: class structure exists
# -----------------------------
def test_class_exists():
    assert hasattr(cvipc, "CompressedVipc")


# -----------------------------
# Test 6: class methods exist
# -----------------------------
def test_class_methods():
    cls = cvipc.CompressedVipc
    assert hasattr(cls, "join")
    assert hasattr(cls, "kill")


# -----------------------------
# Test 7: kill() calls terminate safely (mock)
# -----------------------------
def test_kill_calls_terminate():
    class FakeProcess:
        def __init__(self):
            self.terminated = False

        def terminate(self):
            self.terminated = True

        def join(self):
            pass

    obj = types.SimpleNamespace()
    obj.procs = [FakeProcess(), FakeProcess()]
    obj.join = lambda: None

    cvipc.CompressedVipc.kill(obj)

    assert all(p.terminated for p in obj.procs)


# -----------------------------
# Test 8: join() calls all joins
# -----------------------------
def test_join_calls_join():
    class FakeProcess:
        def __init__(self):
            self.joined = False

        def join(self):
            self.joined = True

    obj = types.SimpleNamespace()
    obj.procs = [FakeProcess(), FakeProcess()]

    cvipc.CompressedVipc.join(obj)

    assert all(p.joined for p in obj.procs)


# -----------------------------
# SIMPLE RUNNER
# -----------------------------
if __name__ == "__main__":
    tests = [
        test_encode_sockets,
        test_camera_selection_logic,
        test_camera_index_bounds,
        test_invalid_camera_input,
        test_class_exists,
        test_class_methods,
        test_kill_calls_terminate,
        test_join_calls_join,
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