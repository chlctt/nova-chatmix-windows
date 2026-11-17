"""Texte der Oberflaeche (de/en). Sprache = Windows-Anzeigesprache, per Umgebungsvariable NOVA_LANG=de|en ueberschreibbar."""
import ctypes
import os

STR = {
    "de": {
        "connected": "Basisstation verbunden – Rad drücken für ChatMix",
        "disconnected": "Basisstation nicht verbunden",
        "devices": "Geräte",
        "apps": "Apps",
        "ch_game": "Game", "ch_chat": "Chat", "ch_medien": "Medien", "ch_aux": "Aux", "ch_mikro": "Mikro",
        "none": "(nicht ändern)",
        "playing": "Spielt gerade Ton ({n})",
        "silent": "Ohne Ton ({n})",
        "autostart": "Mit Windows starten",
        "quit": "Beenden",
        "open": "Öffnen",
        "running": "Nova ChatMix läuft bereits",
        "svv_missing": "{path} fehlt – Routing und Geräteauswahl sind aus (SoundVolumeView von nirsoft.net, x64-Zip entpacken)",
        "svv_ask": "Nova ChatMix braucht das kostenlose Programm SoundVolumeView (NirSoft), um Apps auf Ausgabegeräte zu legen. "
                   "Es wurde nicht gefunden.\n\nSoll es jetzt mit winget installiert werden?\n\n"
                   "Bei „Nein“ wird die App geschlossen.",
        "svv_manual": "SoundVolumeView ist nicht verfügbar (winget fehlt oder die Installation ist fehlgeschlagen).\n\n"
                      "Bitte den x64-Zip von nirsoft.net entpacken und SoundVolumeView.exe hier ablegen:\n{path}\n\n"
                      "Die App wird geschlossen.",
        "dev_missing": "Gerät '{part}' nicht gefunden",
    },
    "en": {
        "connected": "Base station connected – press the wheel for ChatMix",
        "disconnected": "Base station not connected",
        "devices": "Devices",
        "apps": "Apps",
        "ch_game": "Game", "ch_chat": "Chat", "ch_medien": "Media", "ch_aux": "Aux", "ch_mikro": "Mic",
        "none": "(leave unchanged)",
        "playing": "Playing sound ({n})",
        "silent": "No sound ({n})",
        "autostart": "Start with Windows",
        "quit": "Quit",
        "open": "Open",
        "running": "Nova ChatMix is already running",
        "svv_missing": "{path} is missing – routing and device selection are off (extract the x64 zip of SoundVolumeView from nirsoft.net)",
        "svv_ask": "Nova ChatMix needs the free program SoundVolumeView (NirSoft) to move apps to output devices. "
                   "It was not found.\n\nInstall it now with winget?\n\n"
                   "If you choose \"No\", the app will close.",
        "svv_manual": "SoundVolumeView is not available (winget is missing or the installation failed).\n\n"
                      "Please extract the x64 zip from nirsoft.net and put SoundVolumeView.exe here:\n{path}\n\n"
                      "The app will close.",
        "dev_missing": "Device '{part}' not found",
    },
}


def _lang():
    forced = os.environ.get("NOVA_LANG", "").lower()
    if forced in STR:
        return forced
    try:  # LANGID der Windows-Anzeigesprache; Primaersprache 0x07 = Deutsch
        return "de" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x07 else "en"
    except Exception:
        return "en"


LANG = _lang()


def t(key, **kw):
    return STR[LANG].get(key, key).format(**kw)
