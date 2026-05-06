#!/usr/bin/env python3
"""Standalone QR-login tester for the Xiaomi cloud connector.

Run: ./scripts/qr_test.py [country]
  country: cn de i2 ru sg us tw  (default: us)

Saves the QR PNG to /tmp/xiaomi_qr.png, opens it (macOS), then waits up to
5 minutes for you to scan it from the Mi Home app. Prints the resulting
session tokens so you can paste them into HA if needed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import logging  # noqa: E402

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from custom_components.xiaomi_vacuum.cloud import (  # noqa: E402
    _XiaomiCloudConnector,
)


def main() -> int:
    country = sys.argv[1] if len(sys.argv) > 1 else "us"
    print(f"== Xiaomi QR login test (country={country}) ==")

    connector = _XiaomiCloudConnector()

    print("[1/3] Requesting fresh QR + long-polling URL…")
    qr, lp_url, server_timeout = connector.start_qr_login()
    print(f"      lp_url:        {lp_url}")
    print(f"      server timeout: {server_timeout}s")
    print(f"      qr png bytes:  {len(qr)}")

    qr_path = Path("/tmp/xiaomi_qr.png")
    qr_path.write_bytes(qr)
    print(f"      QR saved to:   {qr_path}")
    if sys.platform == "darwin":
        subprocess.run(["open", str(qr_path)], check=False)  # noqa: S603, S607

    print(f"[2/3] Long-polling (single connection, up to {server_timeout}s)…")
    print("      ➜ open Mi Home app, top-right QR scanner, scan now.")
    ok = connector.poll_qr_login(lp_url, timeout=server_timeout)
    if not ok:
        print("[FAIL] Login did not complete (timeout / not scanned / wrong region).")
        return 1

    print("[3/3] Success! Session tokens:")
    print(f"      ssecurity:     {connector._ssecurity}")
    print(f"      service_token: {connector._service_token[:24]}…")
    print(f"      user_id:       {connector._user_id}")

    print("\nOptionally: device list lookup")
    devices = list(connector._iter_devices(country))
    print(f"  found {len(devices)} device(s) in country={country}:")
    for d in devices:
        print(f"   - {d.name!r} model={d.model} did={d.device_id} token={d.token[:6]}…")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
