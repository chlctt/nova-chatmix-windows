"""Probe: liest ALLE HID-Sammlungen der Basisstation und zeigt rohe Nachrichten.

Protokoll-Quelle: https://github.com/Dymstro/nova-chatmix-linux (0BSD).
Usage: python probe.py [seconds]   (GG/Sonar muss geschlossen sein)
"""
import sys
import time

import hid

VID, PID = 0x1038, 0x12E0
TX = 0x06
OPT_CHATMIX_ENABLE = 0x49
MSGLEN = 63


def msg(*b):
    return bytes(b).ljust(MSGLEN, b"\0")


def main(seconds):
    devs = []
    for d in hid.enumerate(VID, PID):
        tag = f"if{d['interface_number']} usage={d['usage_page']:#06x}/{d['usage']:#04x} ..{d['path'][-45:-40].decode(errors='ignore')}"
        dev = hid.device()
        try:
            dev.open_path(d["path"])
        except OSError as e:
            print(f"[{tag}] open fehlgeschlagen: {e}")
            continue
        dev.set_nonblocking(True)
        if d["interface_number"] == 4:
            print(f"[{tag}] enable write -> {dev.write(msg(TX, OPT_CHATMIX_ENABLE, 1))}")
        else:
            print(f"[{tag}] nur lesen")
        devs.append((tag, dev))

    print(f"Lese {seconds}s von {len(devs)} Geraeten: Rad druecken (ChatMix-Modus), dann drehen ...")
    end = time.time() + seconds
    while time.time() < end:
        for tag, dev in devs:
            try:
                m = dev.read(64)
            except OSError as e:
                print(f"[{tag}] read-Fehler: {e}")
                continue
            if m:
                print(f"[{tag}] {list(m[:8])}")
        time.sleep(0.005)

    for tag, dev in devs:
        if "if4" in tag:
            dev.write(msg(TX, OPT_CHATMIX_ENABLE, 0))
        dev.close()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
