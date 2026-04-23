import os
import time
import numpy as np
import pytest

import cereal.messaging as messaging
from openpilot.selfdrive.test.helpers import with_processes
from openpilot.selfdrive.pandad.tests.test_pandad_loopback import setup_pandad, send_random_can_messages

JUNGLE_SPAM = "JUNGLE_SPAM" in os.environ

@pytest.mark.tici
class TestBoarddSpiEdgeCases:
  @classmethod
  def setup_class(cls):
    os.environ['STARTED'] = '1'
    os.environ['SPI_ERR_PROB'] = '0.001'
    if not JUNGLE_SPAM:
      os.environ['BOARDD_LOOPBACK'] = '1'

  # Test 1: Null dat field in CAN frame
  @with_processes(['pandad'])
  def test_null_dat_field_in_can_frame(self):
    """
    A CAN frame with empty/null dat bytes should be handled gracefully.
    pandad must not crash and should either drop or forward the frame.
    """
    setup_pandad()
    sendcan = messaging.pub_sock('sendcan')
    can_sock = messaging.sub_sock('can', conflate=False, timeout=1000)
    time.sleep(1)
    messaging.drain_sock_raw(can_sock)

    # send a CAN frame with empty dat
    msg = messaging.new_message('sendcan', 1)
    msg.valid = True
    msg.sendcan[0].address = 0x100
    msg.sendcan[0].dat = b''      # null / zero-length payload
    msg.sendcan[0].src = 0
    sendcan.send(msg.to_bytes())
    time.sleep(0.5)

    # pandad must still be alive and responding, drain whatever came back
    msgs = messaging.drain_sock(can_sock)
    for m in msgs:
      for frame in m.can:
        assert frame.src <= 4, f"Unexpected src {frame.src} from null-dat frame"

  # Test 2: Empty sendcan list
  @with_processes(['pandad'])
  def test_empty_sendcan_list(self):
    """
    Sending a sendcan message with zero frames must not crash pandad.
    The service should keep running normally afterwards.
    """
    setup_pandad()
    sendcan = messaging.pub_sock('sendcan')
    panda_sock = messaging.sub_sock('pandaStates', conflate=False, timeout=2000)
    time.sleep(1)
    messaging.drain_sock_raw(panda_sock)

    # send genuinely empty sendcan (0 frames)
    msg = messaging.new_message('sendcan', 0)
    msg.valid = True
    sendcan.send(msg.to_bytes())
    time.sleep(0.5)

    msgs = messaging.drain_sock(panda_sock)
    assert len(msgs) > 0, "pandad stopped publishing after empty sendcan, possible crash"
    for m in msgs:
      assert m.valid, "pandaStates marked invalid after empty sendcan"

  # Test 3: Bus number > 3 messages are filtered
  @with_processes(['pandad'])
  def test_high_bus_messages_are_filtered(self):
    """
    Messages received with src > 4 should be filtered out and never
    forwarded. We count them explicitly — expected count is zero.
    """
    setup_pandad()
    sendcan = messaging.pub_sock('sendcan')
    can_sock = messaging.sub_sock('can', conflate=False, timeout=1000)
    time.sleep(1)
    messaging.drain_sock_raw(can_sock)

    send_random_can_messages(sendcan, 20)
    time.sleep(1)

    msgs = messaging.drain_sock(can_sock)
    high_bus_frames = [
      (m.can[i].src, m.can[i].address)
      for m in msgs
      for i in range(len(m.can))
      if m.can[i].src > 4
    ]
    assert len(high_bus_frames) == 0, (
      f"Got {len(high_bus_frames)} frames with src > 4 that should have been filtered: "
      f"{high_bus_frames[:5]}"   # show first 5 offenders
    )

  # Test 4: fanSpeedRpm == 0 edge case
  @with_processes(['pandad'])
  def test_fan_speed_rpm_zero_is_valid(self):
    """
    fanSpeedRpm = 0 is a valid state (fan off / cold start).
    The current check `ps.fanSpeedRpm < 10000` already allows 0,
    but this test explicitly asserts the lower bound is not rejected.
    Also catches any future regression that adds `> 0` guard.
    """
    setup_pandad()
    sock = messaging.sub_sock('peripheralState', conflate=False, timeout=3000)
    time.sleep(2)

    msgs = messaging.drain_sock(sock)
    assert len(msgs) > 0, "No peripheralState messages received"

    fan_speeds = [m.peripheralState.fanSpeedRpm for m in msgs]
    print(f"\nfanSpeedRpm values seen: min={min(fan_speeds)} max={max(fan_speeds)}")

    for rpm in fan_speeds:
      # 0 is explicitly valid; fan make be off
      assert 0 <= rpm < 10000, (
        f"fanSpeedRpm {rpm} is out of valid range [0, 10000)"
      )

  # ── Test 5: Voltage exact boundary values ─────────────────────────────────
  @with_processes(['pandad'])
  def test_voltage_boundary_values(self):
    """
    MISSING FROM: test_spi_corruption()
    Original uses strict < / > so exact boundary values 4000 and 14000
    would wrongly fail. Should be <= / >= — this test catches that regression.
    """
    setup_pandad()
    sock = messaging.sub_sock('pandaStates', conflate=False, timeout=2000)
    time.sleep(2)

    msgs = messaging.drain_sock(sock)
    assert len(msgs) > 0, "No pandaStates messages received"

    for m in msgs:
      ps = m.pandaStates[0]
      assert 4000 <= ps.voltage <= 14000, (
        f"Voltage {ps.voltage} mV outside valid range [4000, 14000]\n"
        f"Note: boundary values 4000 and 14000 are explicitly valid"
      )

  # ── Test 6: uptime lower bound ────────────────────────────────────────────
  @with_processes(['pandad'])
  def test_panda_uptime_is_nonzero(self):
    """
    MISSING FROM: test_spi_corruption()
    Original only checks ps.uptime < 1000.
    uptime = 0 means pandad never properly started — lower bound never checked.
    """
    setup_pandad()
    sock = messaging.sub_sock('pandaStates', conflate=False, timeout=2000)
    time.sleep(2)

    msgs = messaging.drain_sock(sock)
    assert len(msgs) > 0, "No pandaStates messages received"

    for m in msgs:
      ps = m.pandaStates[0]
      assert 0 < ps.uptime < 1000, (
        f"uptime={ps.uptime} invalid — must be > 0 (pandad started) and < 1000"
      )

  # ── Test 7: packet drop ratio ─────────────────────────────────────────────
  @with_processes(['pandad'])
  def test_can_packet_drop_ratio(self):
    """
    MISSING FROM: test_spi_corruption()
    Original only checks total_recv_count > 20 — never checks ratio against
    what was actually sent. Could receive 21/500 and still pass.
    """
    setup_pandad()
    sendcan = messaging.pub_sock('sendcan')
    can_sock = messaging.sub_sock('can', conflate=False, timeout=1000)
    time.sleep(1)
    messaging.drain_sock_raw(can_sock)

    sent_msgs = {bus: list() for bus in range(3)}
    for _ in range(10):
      new_msgs = send_random_can_messages(sendcan, 10)
      for bus, msgs in new_msgs.items():
        sent_msgs[bus].extend(msgs)
      time.sleep(0.1)

    total_sent = sum(len(v) for v in sent_msgs.values())
    time.sleep(1)

    recv_msgs = messaging.drain_sock(can_sock)
    total_recv = sum(len(m.can) for m in recv_msgs)

    assert total_sent > 0, "No messages were sent — send_random_can_messages may have failed"

    ratio = total_recv / total_sent
    print(f"\nSent {total_sent}, received {total_recv} ({ratio:.2%})")
    assert ratio >= 0.8, (
      f"Too many dropped packets — only {ratio:.2%} received\n"
      f"Sent: {total_sent}  Received: {total_recv}"
    )

  # ── Test 8: SPI zero error rate clean baseline ────────────────────────────
  @with_processes(['pandad'])
  def test_spi_zero_error_rate_baseline(self):
    """
    MISSING FROM: test_spi_corruption()
    Tests always run at SPI_ERR_PROB=0.001 — a clean zero-error baseline
    is never verified. With 0 errors, recv ratio must be near 100%.
    """
    os.environ['SPI_ERR_PROB'] = '0'
    setup_pandad()

    sendcan = messaging.pub_sock('sendcan')
    can_sock = messaging.sub_sock('can', conflate=False, timeout=1000)
    time.sleep(1)
    messaging.drain_sock_raw(can_sock)

    sent_msgs = send_random_can_messages(sendcan, 20)
    total_sent = sum(len(v) for v in sent_msgs.values())
    time.sleep(1)

    recv_msgs = messaging.drain_sock(can_sock)
    total_recv = sum(len(m.can) for m in recv_msgs)

    assert total_sent > 0, "send_random_can_messages sent 0 messages"
    ratio = total_recv / total_sent
    print(f"\n[zero error] Sent {total_sent}, received {total_recv} ({ratio:.2%})")
    assert ratio >= 0.95, (
      f"With SPI_ERR_PROB=0, expected >=95% delivery, got {ratio:.2%}"
    )

    # restore default
    os.environ['SPI_ERR_PROB'] = '0.001'