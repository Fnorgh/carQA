import signal
import subprocess
import time

import pytest

# NOTE: You cannot import or call C++ code directly from Python.
# "#include" is C++ syntax and is NOT valid in a Python file.
# To test a C++ binary (like bridge.cc), you must first compile it into an
# executable, then launch that executable as a subprocess using subprocess.Popen().

# NOTE: pytest discovers test classes that start with "Test" (capital T),
# and test methods that start with "test_". A class named "testBridge"
# (lowercase t) will be silently ignored by pytest.

class TestBridge:

    def test_bridge_default_mode(self):
        # subprocess.Popen() launches the compiled binary as a child process.
        # The argument is a list: the first item is the path to the executable,
        # followed by any command-line arguments (argc/argv in C++ terms).
        # With no extra args, bridge.cc sets is_zmq_to_msgq = false (argc <= 2)
        # and ip defaults to "127.0.0.1".

        # TODO: replace "./bridge" with the actual path to the compiled binary.
        # You must compile bridge.cc into an executable before running this test.
        proc = subprocess.Popen(["./bridge"])

        # TODO: time.sleep() gives the process time to start up before we stop it.
        # The bridge runs an infinite loop (while !do_exit), so we must
        # interrupt it manually — otherwise this test will hang forever.
        time.sleep(0.1)

        # signal.SIGINT is the same as pressing Ctrl+C in a terminal.
        # bridge.cc uses an ExitHandler (do_exit) that catches this signal
        # and breaks out of the while loop cleanly.
        proc.send_signal(signal.SIGINT)

        # proc.wait() blocks until the child process exits.
        # timeout=2 means: if the process hasn't exited in 2 seconds, raise an error.
        proc.wait(timeout=2)

        # proc.returncode is the value returned by main() in the C++ program.
        # bridge.cc returns 0 at the end of main(), so we assert that here.
        assert proc.returncode == 0

    def test_bridge_zmq_to_msgq_mode(self):
        # Passing 2+ arguments after the binary name sets argc > 2 in C++,
        # which makes is_zmq_to_msgq = true in bridge.cc.
        # argv[1] = ip address, argv[2] = whitelist string (service names).

        # TODO: replace "./bridge" with the actual path to the compiled binary.
        # TODO: replace "controlsState" with a service name you know exists
        # in the services list (check cereal/services.py for valid names).
        proc = subprocess.Popen(["./bridge", "127.0.0.1", "controlsState"])

        time.sleep(0.1)
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=2)
        assert proc.returncode == 0
