"""Fenster + Tray fuer Nova ChatMix. Start: pythonw ui.py [--min]

Aenderungen wirken sofort und werden in config.toml gespeichert.
"""
import ctypes
import re
import shutil
import socket
import subprocess
import sys
import threading
import winreg
from pathlib import Path

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw

import chatmix
from i18n import t

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "NovaChatMix"
CHANNEL_LABELS = {k: t(f"ch_{k}") for k in chatmix.CHANNELS}  # Config-Schluessel -> Anzeigename
NONE = t("none")  # Mikro: Standard-Aufnahmegerät unberührt lassen
HIDDEN = ("sonar", "steam streaming")  # virtuelle Geraete, die man nie als Ausgabe will


def autostart_get():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def autostart_set(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            if getattr(sys, "frozen", False):  # als .exe
                cmd = f'"{sys.executable}" --min'
            else:
                pyw = Path(sys.executable).with_name("pythonw.exe")
                cmd = f'"{pyw}" "{Path(__file__).resolve()}" --min'
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


def device_label(dev_id):  # "2- Arctis ...\Device\Kopfhoerer\Render" -> "Kopfhoerer (2- Arctis ...)"
    parts = dev_id.split("\\")
    return f"{parts[2]} ({parts[0]})"


def device_key(dev_id):  # Port-Zaehler entfernen, damit die Config USB-Port-unabhaengig bleibt
    return re.sub(r"^\d+- ", "", dev_id)


def tray_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, 60, 60), fill=(30, 144, 255, 255))
    d.rectangle((26, 14, 38, 50), fill=(255, 255, 255, 255))
    return img


class App(ctk.CTk):
    def __init__(self, engine, thread=None, start_hidden=False):
        super().__init__()
        self.engine, self.thread = engine, thread
        self.title("Nova ChatMix")
        self.geometry("580x760")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)  # X = in den Tray
        self.shown_apps, self.shown_devs = None, None
        self.silent_open = False  # Gruppe "Ohne Ton" eingeklappt

        self.status = ctk.CTkLabel(self, text="", anchor="w", justify="left", wraplength=540)
        self.status.pack(fill="x", padx=16, pady=(14, 4))
        self.bars = {}
        for key in ("game", "chat"):
            label = t(f"ch_{key}")
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label, width=50, anchor="w").pack(side="left")
            bar = ctk.CTkProgressBar(row)
            bar.pack(side="left", fill="x", expand=True, padx=8)
            val = ctk.CTkLabel(row, text="-", width=36)
            val.pack(side="left")
            self.bars[key] = (bar, val)

        ctk.CTkLabel(self, text=t("devices"), anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=16, pady=(16, 2))
        self.menus = {}
        for key in (*chatmix.CHANNELS, "mikro"):
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=t(f"ch_{key}"), width=60, anchor="w").pack(side="left")
            menu = ctk.CTkOptionMenu(row, values=["-"], command=lambda v, k=key: self.set_device(k, v))
            menu.pack(side="left", fill="x", expand=True)
            self.menus[key] = menu

        ctk.CTkLabel(self, text=t("apps"), anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=16, pady=(16, 2))
        self.apps_frame = ctk.CTkScrollableFrame(self)
        self.apps_frame.pack(fill="both", expand=True, padx=16, pady=2)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=12)
        self.auto = ctk.CTkSwitch(bottom, text=t("autostart"), command=lambda: autostart_set(bool(self.auto.get())))
        self.auto.pack(side="left")
        if autostart_get():
            self.auto.select()
        ctk.CTkButton(bottom, text=t("quit"), width=90, command=self.quit_app).pack(side="right")

        self.tray = pystray.Icon("nova-chatmix", tray_image(), "Nova ChatMix", pystray.Menu(
            pystray.MenuItem(t("open"), lambda: self.after(0, self.deiconify), default=True),
            pystray.MenuItem(t("quit"), lambda: self.after(0, self.quit_app)),
        ))
        self.tray.run_detached()
        if start_hidden:
            self.withdraw()
        self.refresh()

    def set_device(self, key, label):
        if label == NONE:
            self.engine.cfg["devices"].pop(key, None)
        else:
            dev_id = next(i for i in self.engine.devices + self.engine.mics if device_label(i) == label)
            self.engine.cfg["devices"][key] = device_key(dev_id)
        chatmix.save_cfg(self.engine.cfg)
        self.engine.reload = True

    def set_channel(self, app, label):
        self.engine.cfg["apps"][app] = next(k for k, v in CHANNEL_LABELS.items() if v == label)
        chatmix.save_cfg(self.engine.cfg)

    def refresh(self):
        e = self.engine
        self.status.configure(text=t("connected" if e.connected else "disconnected")
                              + (f"\n⚠ {e.error}" if e.error else ""))
        for i, key in enumerate(("game", "chat")):
            bar, val = self.bars[key]
            v = e.vols[i] if e.vols else None
            bar.set((v or 0) / 100)
            val.configure(text="-" if v is None else str(v))

        def labels(ids):
            return tuple(sorted(device_label(i) for i in ids if not any(h in i.lower() for h in HIDDEN)))

        outs, ins = labels(e.devices), labels(e.mics)
        if outs and (outs, ins) != self.shown_devs:
            self.shown_devs = (outs, ins)
            d = e.cfg["devices"]
            for key, menu in self.menus.items():
                mic = key == "mikro"
                pool, names = (e.mics, ins) if mic else (e.devices, outs)
                menu.configure(values=list(names) + ([NONE] if mic else []))
                part = (d.get(key) or ("" if mic else d["game"])).lower()  # chat/medien/aux ohne Eintrag = Game-Gerät
                menu.set(next((device_label(i) for i in pool if part and part in i.lower() and device_label(i) in names), NONE if mic else names[0]))

        known = set(e.apps) | {k for k in e.cfg["apps"] if k != "default"}
        playing = tuple(sorted(known & e.active))
        silent = tuple(sorted(known - e.active))
        if (playing, silent) != self.shown_apps:
            self.shown_apps = (playing, silent)
            self.build_apps(playing, silent)
        self.after(300, self.refresh)

    def build_apps(self, playing, silent):
        for w in self.apps_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.apps_frame, text=t("playing", n=len(playing)), anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x", pady=(0, 2))
        for name in playing:
            self.app_row(name)
        # Ohne Ton: standardmaessig eingeklappt
        arrow = "▼" if self.silent_open else "▶"
        ctk.CTkButton(self.apps_frame, text=f"{arrow} {t('silent', n=len(silent))}", anchor="w", fg_color="transparent",
                      hover_color=("gray80", "gray25"), command=self.toggle_silent).pack(fill="x", pady=(10, 2))
        if self.silent_open:
            for name in silent:
                self.app_row(name)

    def toggle_silent(self):
        self.silent_open = not self.silent_open
        self.shown_apps = None  # erzwingt Neuaufbau

    def app_row(self, name):
        row = ctk.CTkFrame(self.apps_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=name, anchor="w").pack(side="left", fill="x", expand=True)
        seg = ctk.CTkSegmentedButton(row, values=list(CHANNEL_LABELS.values()), command=lambda v, n=name: self.set_channel(n, v))
        seg.set(CHANNEL_LABELS.get(chatmix.channel_of(self.engine.cfg, name), ""))
        seg.pack(side="right")

    def quit_app(self):
        self.engine.stop.set()
        if self.thread:
            self.thread.join(3)  # Engine setzt Lautstaerken zurueck und schaltet ChatMix aus
        self.tray.stop()
        self.destroy()


def msgbox(text, flags):
    return ctypes.windll.user32.MessageBoxW(0, text, "Nova ChatMix", flags)


def ensure_svv():
    """SoundVolumeView fehlt: per winget installieren, wenn der Nutzer zustimmt. True = jetzt vorhanden."""
    if msgbox(t("svv_ask"), 0x24) != 6:  # MB_YESNO | MB_ICONQUESTION; 6 = Ja
        return False
    winget = shutil.which("winget")
    if winget:
        subprocess.run([winget, "install", "--id", "NirSoft.SoundVolumeView", "--exact", "--silent",
                        "--accept-source-agreements", "--accept-package-agreements"],
                       creationflags=subprocess.CREATE_NO_WINDOW)
        chatmix.SVV = chatmix.find_svv() or chatmix.SVV
    if not chatmix.SVV.exists():
        msgbox(t("svv_manual", path=chatmix.SVV), 0x10)
        return False
    return True


def main():
    lock = socket.socket()  # Einzelinstanz: zweiter Start scheitert am belegten Port
    try:
        lock.bind(("127.0.0.1", 47653))
    except OSError:  # ohne Konsole sieht man SystemExit-Texte nicht -> Meldungsfenster
        ctypes.windll.user32.MessageBoxW(0, t("running"), "Nova ChatMix", 0x40)
        raise SystemExit(1)
    if not chatmix.SVV.exists() and not ensure_svv():
        raise SystemExit(1)
    ctk.set_appearance_mode("dark")
    engine = chatmix.Engine()
    thread = threading.Thread(target=engine.run, daemon=True)
    thread.start()
    App(engine, thread, start_hidden="--min" in sys.argv).mainloop()


if __name__ == "__main__":
    main()
