"""ChatMix + App-Routing fuer Arctis Nova Pro Wireless unter Windows, ohne GG/Sonar.

- Rad der Basisstation -> Lautstaerke pro App (Kanaele game/chat; aux bleibt unberuehrt).
- config.toml legt fest, welche App auf welchem Kanal/Geraet ausgibt.
Protokoll: https://github.com/Dymstro/nova-chatmix-linux (0BSD).
GG/Sonar muss geschlossen sein. Beenden mit Strg+C (Konsole) bzw. ueber ui.py.
Routing braucht NirSoft SoundVolumeView: tools/svv/SoundVolumeView.exe (nirsoft.net).

Aufruf: python chatmix.py [--devices | --apps]
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from pathlib import Path

import comtypes
import hid
from pycaw.api.audiopolicy import IAudioSessionControl2
from pycaw.pycaw import AudioSession, AudioUtilities

from i18n import t

FROZEN = getattr(sys, "frozen", False)
HERE = Path(sys.executable).parent if FROZEN else Path(__file__).parent  # als .exe: tools/ liegt daneben
RES = Path(getattr(sys, "_MEIPASS", HERE))  # in die .exe gebuendelte Dateien (config.example.toml)
# als .exe: Config in %APPDATA%, weil ein Paketmanager (winget) den Programmordner beim Update ersetzt
CFG = Path(os.environ.get("APPDATA", HERE)) / "NovaChatMix" / "config.toml" if FROZEN else HERE / "config.toml"


def find_svv():
    """SoundVolumeView: tools/svv neben dem Programm, sonst PATH, sonst winget-Links-Ordner (PATH kennt ihn evtl. noch nicht)."""
    links = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links" / "SoundVolumeView.exe"
    candidates = (HERE / "tools" / "svv" / "SoundVolumeView.exe", shutil.which("SoundVolumeView"), links)
    return next((Path(p) for p in candidates if p and Path(p).is_file()), None)


SVV = find_svv() or HERE / "tools" / "svv" / "SoundVolumeView.exe"
VID, PID, IFACE = 0x1038, 0x12E0, 4
TX = 0x06
OPT_CHATMIX_ENABLE, OPT_CHATMIX, OPT_SONAR_ICON = 0x49, 0x45, 0x8D
MSGLEN = 63
CHANNELS = ("game", "chat", "medien", "aux")  # Ausgabekanaele; Rad regelt nur game/chat. Eingabe: Schluessel "mikro"
IGNORE = {"audiodg.exe"}  # Windows-Audio-Engine, nie routen oder in der Lautstaerke aendern
TICK = 2  # Sekunden zwischen Routing-/Lautstaerke-Nachzug fuer neue Apps


def msg(*b):
    return bytes(b).ljust(MSGLEN, b"\0")


# --- Konfiguration -------------------------------------------------------

def load_cfg():
    # config.toml ist persoenlich (nicht im Repo); ohne sie gilt die Vorlage config.example.toml
    src = next(p for p in (CFG, RES / "config.example.toml") if p.exists())
    return tomllib.loads(src.read_text(encoding="utf-8"))


def save_cfg(cfg):
    # ponytail: Kommentare der Datei gehen beim Speichern verloren; Literal-Strings wegen "\" in Geraete-IDs.
    lines = ["# Wird von der UI geschrieben. Kanaele: game | chat | aux", "[devices]"]
    lines += [f"{k} = '{v}'" for k, v in cfg["devices"].items()]
    lines += ["", "[apps]", f"default = '{cfg['apps'].get('default', 'game')}'"]
    lines += [f"'{k}' = '{v}'" for k, v in sorted(cfg["apps"].items()) if k != "default"]
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Basisstation --------------------------------------------------------

def open_devices():
    # Zwei HID-Sammlungen auf Interface 4: eine nimmt Befehle an (0xffc0),
    # die andere liefert die Drehwerte (0xff00). Wir oeffnen beide und lesen von beiden.
    devs = []  # Liste von (Geraet, kann_schreiben)
    for d in hid.enumerate(VID, PID):
        if d["interface_number"] != IFACE:
            continue
        dev = hid.device()
        dev.open_path(d["path"])
        dev.set_nonblocking(True)
        writer = dev.write(msg(TX, OPT_CHATMIX_ENABLE, 1)) > 0
        if writer:
            dev.write(msg(TX, OPT_SONAR_ICON, 1))  # wie im Linux-Original, vermutlich nur das Icon
        devs.append((dev, writer))
    if not any(w for _, w in devs):
        for dev, _ in devs:
            dev.close()
        raise OSError("Basisstation nicht gefunden")
    return devs


# --- Geraete / Routing (SoundVolumeView) ---------------------------------

def render_devices(direction="Render"):
    """Aktive Geraete (Render = Ausgabe, Capture = Eingabe) als Liste von 'Command-Line Friendly ID'."""
    out = Path(tempfile.gettempdir()) / "novachatmix_devices.csv"
    subprocess.run([str(SVV), "/scomma", str(out)], check=True)
    with open(out, encoding="utf-8-sig", newline="") as f:
        return [r["Command-Line Friendly ID"] for r in csv.DictReader(f)
                if r["Type"] == "Device" and r["Direction"] == direction and r["Device State"] == "Active"]


def find_device(ids, part):
    # Teilstring, weil Windows einen portabhaengigen Zaehler voranstellt ("2- Arctis ...")
    hits = [i for i in ids if part.lower() in i.lower()]
    if not hits:
        raise LookupError(t("dev_missing", part=part))
    return hits[0]


def channel_of(cfg, name):
    return cfg["apps"].get(name, cfg["apps"].get("default", "game"))


def route(cfg, ids, routed, names):
    """Legt neu aufgetauchte Apps einmalig auf das Geraet ihres Kanals."""
    for name in names:
        dev_id = ids.get(channel_of(cfg, name), ids["game"])
        if routed.get(name) != dev_id:
            subprocess.run([str(SVV), "/SetAppDefault", dev_id, "all", name], check=False)
            routed[name] = dev_id
            print(f"{name} -> {dev_id.split(chr(92))[0]}")


# --- Lautstaerke pro App -------------------------------------------------

def all_sessions():
    """Sessions auf ALLEN aktiven Ausgabegeraeten (pycaw.GetAllSessions sieht nur das Standardgeraet)."""
    out = []
    for dev in AudioUtilities.GetAllDevices(data_flow=0, device_state=1):  # eRender, aktiv
        try:
            en = dev.AudioSessionManager.GetSessionEnumerator()
            for i in range(en.GetCount()):
                ctl = en.GetSession(i)
                if ctl is not None:
                    out.append(AudioSession(ctl.QueryInterface(IAudioSessionControl2)))
        except Exception:  # Geraet ohne Session-Manager (z.B. virtuell/gesperrt)
            pass
    return out


def app_names():
    """{Prozessname: spielt gerade Ton} (Session-Status 'aktiv' = Stream laeuft)."""
    names = {}
    for s in all_sessions():
        try:
            if s.Process and s.Process.name().lower() not in IGNORE:
                n = s.Process.name().lower()
                names[n] = names.get(n, False) or s.State == 1
        except Exception:  # Prozess beendet
            pass
    return names


def apply(cfg, game, chat):
    for s in all_sessions():
        try:
            name = s.Process.name().lower() if s.Process else None
            if name and name not in IGNORE:
                vol = {"game": game, "chat": chat}.get(channel_of(cfg, name), 100)  # aux: immer 100
                s.SimpleAudioVolume.SetMasterVolume(vol / 100, None)
        except Exception:  # Session verschwunden o.ae.
            pass


# --- Engine --------------------------------------------------------------

class Engine:
    """Hintergrundschleife; UI und Konsole lesen nur die Attribute."""

    def __init__(self):
        self.cfg = load_cfg()
        self.vols = None      # (game, chat) vom Rad, None bis zur ersten Drehung
        self.connected = False
        self.svv = SVV.exists()  # ohne SoundVolumeView laeuft nur das Rad, kein Routing/keine Geraete
        self.error = "" if self.svv else t("svv_missing", path=SVV)
        self.apps = []        # Apps mit Audio-Session (egal ob gerade Ton)
        self.active = set()   # davon: Apps, die gerade Ton ausgeben
        self.devices = []     # aktive Ausgabegeraete (Command-Line Friendly IDs)
        self.mics = []        # aktive Eingabegeraete
        self.stop = threading.Event()
        self.reload = False   # True -> Geraete neu aufloesen (nach Aenderung von cfg["devices"])

    def run(self):
        comtypes.CoInitialize()  # noetig, wenn run() in einem Thread laeuft
        devs, ids, routed = None, None, {}
        last = retry_ids = retry_dev = 0
        try:
            while not self.stop.is_set():
                now = time.time()
                if self.reload:
                    ids, self.reload, retry_ids = None, False, 0
                if ids is None and self.svv and now >= retry_ids:
                    try:
                        self.devices, self.mics = render_devices(), render_devices("Capture")
                        d = self.cfg["devices"]
                        # chat/medien/aux ohne eigenen Eintrag laufen ueber das Game-Geraet
                        ids = {k: find_device(self.devices, d.get(k) or d["game"]) for k in CHANNELS}
                        routed.clear()
                        self.error = ""
                        if d.get("mikro"):  # Standard-Aufnahmegeraet einmalig setzen (nicht dauernd, sonst Streit mit Windows)
                            mic = find_device(self.mics, d["mikro"])
                            subprocess.run([str(SVV), "/SetDefault", mic, "all"], check=False)
                    except (LookupError, OSError, subprocess.CalledProcessError) as e:
                        self.error, retry_ids = str(e), now + TICK
                if devs is None and now >= retry_dev:
                    try:
                        devs = open_devices()
                        self.connected = True
                        routed.clear()  # nach Reconnect neu zuweisen
                        print("verbunden")
                    except OSError:
                        retry_dev = now + 2
                m = None
                if devs:
                    try:
                        reads = [d.read(MSGLEN) for d, _ in devs]
                        m = next((r for r in reads if r and r[1] == OPT_CHATMIX), None)
                    except OSError:  # Station getrennt / Standby -> neu verbinden
                        devs, self.connected = None, False
                        print("getrennt")
                if m:
                    self.vols = (m[2], m[3])
                    apply(self.cfg, *self.vols)
                    last = now
                    print(f"game={m[2]} chat={m[3]}")
                elif now - last > TICK:  # neu gestartete Apps nachziehen
                    names = app_names()
                    self.apps = sorted(names)
                    self.active = {n for n, a in names.items() if a}
                    if ids:
                        route(self.cfg, ids, routed, names)
                    if self.vols:
                        apply(self.cfg, *self.vols)
                    last = now
                else:
                    time.sleep(0.02)
        finally:
            apply(self.cfg, 100, 100)  # App-Lautstaerken zuruecksetzen, sonst bleibt z.B. Firefox stumm
            for dev, writer in devs or []:
                if writer:
                    dev.write(msg(TX, OPT_CHATMIX_ENABLE, 0))
                    dev.write(msg(TX, OPT_SONAR_ICON, 0))


def main():
    if "--apps" in sys.argv:
        print("\n".join(f"{n}{' *' if a else ''}" for n, a in sorted(app_names().items())))  # * = spielt Ton
    elif "--devices" in sys.argv:
        if not SVV.exists():
            raise SystemExit(t("svv_missing", path=SVV))
        print("\n".join(render_devices()))
    else:
        try:
            engine = Engine()
            if engine.error:
                print(engine.error)
            engine.run()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
