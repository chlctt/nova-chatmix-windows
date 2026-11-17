# Code signing policy

> **Status:** application to the SignPath Foundation pending. Until it is approved, the released `NovaChatMix.exe` is **not** signed.

Free code signing provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org).

## What is signed

Only `NovaChatMix.exe`, built from this repository by the GitHub Actions workflow [`.github/workflows/release.yml`](.github/workflows/release.yml) on GitHub-hosted runners. Third-party files in the package (Python runtime, libraries) are not re-signed. Every release needs manual approval in SignPath before it is signed.

## Team roles

This is a one-person project.

- Committers and reviewers: [chlctt](https://github.com/chlctt)
- Approvers: [chlctt](https://github.com/chlctt)

The maintainer uses multi-factor authentication for GitHub and for the Microsoft account used to sign in to SignPath.

## Privacy policy

This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.

The only network access is on request: if SoundVolumeView is missing, the program asks whether it may install it with `winget`, which downloads it from NirSoft via the Windows Package Manager. No telemetry, no accounts, no analytics.

## System changes and removal

The program does what the user configures in its window: it moves apps to chosen output devices and can set the default microphone through Windows' own per-app audio settings, and it can register itself for autostart (switch in the window). It does not install drivers or services. These Windows settings persist after exit and can be reset in *Settings -> System -> Sound -> Volume mixer*.

To remove the program, switch off autostart in the window and delete the program folder (or `winget uninstall`, once it is published there). Settings live in `%APPDATA%\NovaChatMix`.
