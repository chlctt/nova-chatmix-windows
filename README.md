# Nova ChatMix for Windows

A small replacement for the parts of **SteelSeries GG / Sonar** that matter for the **Arctis Nova Pro Wireless**: the ChatMix wheel, per-app output devices and a channel mixer. No virtual audio driver, no GG running in the background.

*Deutsche Version: [weiter unten](#nova-chatmix-für-windows-deutsch).*

> Unofficial, not affiliated with or endorsed by SteelSeries. The base station protocol was reverse-engineered by others (see [Credits](#credits)). Use at your own risk.

## What it does

- **ChatMix wheel**: turn the wheel on the base station and the volume of your *game* apps and *chat* apps (Discord, Teams, TeamSpeak, ...) is mixed against each other, per app.
- **Channels**: `Game`, `Chat`, `Media`, `Aux` (outputs) and `Mic` (input). Each channel can use its own Windows device, e.g. headset for Game/Chat and a soundbar for Aux.
- **Per-app routing**: assign every app to a channel; it is moved to that channel's output device automatically.
- **Window + tray icon** (English/German, picked from the Windows display language). Apps that are currently playing sound are listed first, the rest is collapsed.
- **Autostart** switch, start minimized to the tray.

Not included: EQ, noise gate/cancelling, spatial audio. Use the base station's own EQ or something like Equalizer APO for that.

## Requirements

- Windows 10/11
- Arctis Nova Pro Wireless base station (USB ID `1038:12E0`). Other models are untested.
- [NirSoft SoundVolumeView](https://www.nirsoft.net/utils/sound_volume_view.html) (freeware, closed source, unsigned). It sets the output device per app, which Windows only exposes through an undocumented API. If it is missing at startup, the app asks whether it may install it with `winget` (`NirSoft.SoundVolumeView`); if you decline, the app closes.

## Install

1. Download `NovaChatMix-win64.zip` from the [releases page](../../releases) and **unzip it completely** (do not start the exe from inside the zip viewer).
2. **Quit SteelSeries GG completely** (tray icon -> Exit, and check the task manager). GG and this tool must not run at the same time; both talk to the base station.
3. Start `NovaChatMix.exe`, answer the SoundVolumeView question if it appears, press the wheel on the base station once to switch it to ChatMix mode, then turn it.

The download is **unsigned**, so Windows SmartScreen or an antivirus scanner may warn about it. You can build it yourself (below).

SoundVolumeView is looked up in `tools\svv\SoundVolumeView.exe` next to the exe, then in the `PATH` and in winget's link folder. To install it yourself: `winget install NirSoft.SoundVolumeView`, or extract the x64 zip from nirsoft.net to `tools\svv\`.

## Run from source

Needs Python 3.11 or newer.

```powershell
git clone https://github.com/chlctt/nova-chatmix-windows
cd nova-chatmix-windows
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python ui.py          # with console output
.venv\Scripts\pythonw.exe ui.py     # without console window
```

Build the exe with PyInstaller (not part of `requirements.txt`):

```powershell
.venv\Scripts\pip install pyinstaller
.venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --name NovaChatMix --version-file version_info.txt `
  --collect-data customtkinter --hidden-import pystray._win32 --add-data "config.example.toml;." ui.py
```

The result is the folder `dist\NovaChatMix\` (about 43 MB). Releases are built the same way by the GitHub Actions workflow in `.github/workflows/release.yml` (see the [code signing policy](CODE_SIGNING_POLICY.md)).

## Configuration

Everything can be set in the window. Settings are saved to `%APPDATA%\NovaChatMix\config.toml` (when running from source: `config.toml` in the project folder), created from `config.example.toml`; see that file for the format. Device values are parts of the Windows device name, so they survive USB port changes.

Helpers when running from source:

```powershell
.venv\Scripts\python chatmix.py --devices   # list active playback devices
.venv\Scripts\python chatmix.py --apps      # apps with an audio session (* = playing)
.venv\Scripts\python chatmix.py             # headless, no window
.venv\Scripts\python probe.py 20            # raw base station messages (for other firmware/models)
```

## Behaviour to know

- On exit all app volumes are reset to 100 % and the base station leaves ChatMix mode.
- Per-app device assignments and the microphone default are persisted by Windows. They stay after exit; reset them in *Settings -> System -> Sound -> Volume mixer*.
- Windows displays a device counter ("2- Arctis ...") that depends on the USB port. Configuration matches on the name without it.
- Re-enabling GG gives you Sonar back as before.

## How it works

1. The base station exposes two vendor HID collections on USB interface 4. One accepts commands (enable ChatMix mode), the other reports wheel values (`[7, 0x45, game, chat, ...]`, 0-100).
2. Per-app volume is set through the Windows Core Audio session API ([pycaw](https://github.com/AndreMiras/pycaw)) on all active playback devices.
3. Output devices per app and the default microphone are set with SoundVolumeView (`/SetAppDefault`, `/SetDefault`).

## Credits

The HID protocol comes from [nova-chatmix-linux](https://github.com/Dymstro/nova-chatmix-linux) by Dymstro (0BSD). This project is an independent Windows implementation and shares no code with it.

## Code signing policy

Release builds are planned to be signed with free code signing provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org) (application pending; releases are unsigned until then). See [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md).

## License

[0BSD](LICENSE). SoundVolumeView is separate software by NirSoft and is not distributed with this repository.

---

# Nova ChatMix für Windows (Deutsch)

Kleiner Ersatz für die Teile von **SteelSeries GG / Sonar**, die beim **Arctis Nova Pro Wireless** wirklich gebraucht werden: ChatMix-Rad, Ausgabegerät pro App und Kanal-Mixer. Ohne virtuellen Audiotreiber und ohne im Hintergrund laufendes GG.

> Inoffiziell, nicht mit SteelSeries verbunden. Das Protokoll der Basisstation haben andere per Reverse Engineering ermittelt (siehe Credits). Nutzung auf eigene Gefahr.

## Funktionen

- **ChatMix-Rad**: Beim Drehen werden *Game*-Apps und *Chat*-Apps (Discord, Teams, TeamSpeak, ...) pro App gegeneinander gemischt.
- **Kanäle**: `Game`, `Chat`, `Medien`, `Aux` (Ausgabe) und `Mikro` (Eingabe), jeweils mit eigenem Windows-Gerät, zum Beispiel Headset für Game/Chat und Soundbar für Aux.
- **Routing pro App**: Jede App wird einem Kanal zugeordnet und automatisch auf dessen Ausgabegerät gelegt.
- **Fenster + Tray-Icon** (Deutsch/Englisch nach Windows-Anzeigesprache). Apps, die gerade Ton ausgeben, stehen oben, der Rest ist eingeklappt.
- **Autostart**-Schalter, Start minimiert im Tray.

Nicht enthalten: EQ, Gate/Rauschunterdrückung, Raumklang. Dafür den EQ der Basisstation oder z. B. Equalizer APO nutzen.

## Voraussetzungen

- Windows 10/11
- Arctis Nova Pro Wireless Basisstation (USB-ID `1038:12E0`), andere Modelle sind ungetestet
- [NirSoft SoundVolumeView](https://www.nirsoft.net/utils/sound_volume_view.html) (Freeware, closed source, nicht signiert). Es setzt das Ausgabegerät pro App, was Windows nur über eine undokumentierte Schnittstelle anbietet. Fehlt es beim Start, fragt die App, ob sie es per `winget` installieren darf (`NirSoft.SoundVolumeView`). Bei „Nein“ schließt sich die App.

## Installation

1. `NovaChatMix-win64.zip` von der [Releases-Seite](../../releases) laden und **komplett entpacken** (die `.exe` nicht direkt im ZIP-Fenster starten).
2. **SteelSeries GG ganz beenden** (Tray-Icon -> Beenden, im Task-Manager prüfen). GG und dieses Tool dürfen nicht gleichzeitig laufen, beide sprechen mit der Basisstation.
3. `NovaChatMix.exe` starten, die Frage zu SoundVolumeView beantworten (falls sie erscheint), das Rad an der Basisstation einmal drücken (ChatMix-Modus) und drehen.

Der Download ist **nicht signiert**, Windows SmartScreen oder ein Virenscanner können davor warnen. Du kannst ihn selbst bauen (siehe englischer Teil, „Run from source“).

SoundVolumeView wird in `tools\svv\SoundVolumeView.exe` neben der `.exe` gesucht, danach im `PATH` und im Link-Ordner von winget. Selbst installieren: `winget install NirSoft.SoundVolumeView` oder den x64-Zip von nirsoft.net nach `tools\svv\` entpacken.

## Konfiguration

Alles lässt sich im Fenster einstellen. Die Einstellungen liegen unter `%APPDATA%\NovaChatMix\config.toml` (beim Start aus dem Quellcode: `config.toml` im Projektordner), Vorlage ist `config.example.toml`. Geräte werden über einen Teil des Windows-Gerätenamens angegeben und überstehen deshalb einen USB-Portwechsel. Hilfsaufrufe aus dem Quellcode: `chatmix.py --devices`, `chatmix.py --apps`, `probe.py`.

## Hinweise

- Beim Beenden gehen alle App-Lautstärken auf 100 % zurück, und die Basisstation verlässt den ChatMix-Modus.
- Zuordnungen pro App und das Standard-Mikrofon merkt sich Windows dauerhaft. Zurücksetzen unter *Einstellungen -> System -> Sound -> Lautstärkemixer*.
- Mit wieder gestartetem GG ist Sonar wie vorher da.

## Credits und Lizenz

Code-Signing: Release-Builds sollen mit der kostenlosen Signierung von [SignPath.io](https://signpath.io) (Zertifikat der [SignPath Foundation](https://signpath.org)) signiert werden, der Antrag ist noch offen, bis dahin sind die Releases unsigniert. Siehe [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md).

Das HID-Protokoll stammt aus [nova-chatmix-linux](https://github.com/Dymstro/nova-chatmix-linux) von Dymstro (0BSD). Dieses Projekt ist eine eigenständige Windows-Umsetzung ohne gemeinsamen Code. Lizenz: [0BSD](LICENSE). SoundVolumeView ist eine eigene Software von NirSoft und liegt diesem Repository nicht bei.
