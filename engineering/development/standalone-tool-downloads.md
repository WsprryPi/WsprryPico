# Standalone USB installer prerequisites and tool cleanup

The standalone USB installer runs on native macOS and Linux with Python 3.10
or newer and `curl`. Missing or older Python is reported before bootstrap
downloads begin, with the detected version and installation instructions.
Windows, Git Bash and WSL are unsupported and are rejected before USB access.

Install or upgrade also needs a USB-enabled picotool 2.3 or newer within 2.x.
The installer checks its version and the command options required for backup,
programming and verification. An existing compatible executable is used without
replacement. `--picotool /absolute/path` selects an existing executable and
never falls back to a download if that selection fails.

If no compatible executable is available on `PATH`, the installer checks its private cache and verifies a retained package before reuse. Reusing an existing executable or cached package needs no download consent. If neither is available, an interactive terminal offers an official download; an unattended command must explicitly allow it with `--download-picotool`. Flash confirmation through `--yes` does not authorize downloading tools. Requirements and available backup space are checked before firmware image resolution and device maintenance.

```sh
python3 scripts/usb_installer.py upgrade --branch devel \
  --device SERIAL --board pico2_w --yes --download-picotool --tool-cleanup remove
```

The same arguments work with the piped `install_usb.sh` bootstrap. Interactive
install/upgrade commands may omit `--device` to select a Pico from the terminal
menu. Tool download and cleanup prompts read the controlling terminal, leaving
piped script input and JSON stdout separate.

## Official packages and verification

The automatic download uses the reviewed picotool 2.3.1 packages from
[Raspberry Pi's v2.3.1-0 release](https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.3.1-0):

- macOS: the universal Intel/Apple Silicon ZIP.
- Linux ARM64: the AArch64 tarball, including 64-bit Raspberry Pi OS.
- Linux x86-64: the x86-64 tarball.

Other architectures require an existing compatible picotool or a supported
host. An executable that cannot run reports architecture/runtime-library
guidance. No SDK, compiler or package manager is installed. System tools and
`PATH` remain unchanged.

Archive size and SHA-256 are checked before extraction or execution. Extraction
rejects links, special files, path traversal, duplicate paths and oversized
contents. The package's support files remain alongside the executable. A
private copy of the verified archive allows later uses to check cached files
against the official bytes, including detection of altered local receipts.

## Cleanup and recovery

Verified packages are reused under `~/.cache/wsprrypico-usb/tools`, without a
new copy for each update. A lock protects managed tools throughout an update
or recovery. Firmware transactions and backups remain under their existing
private state directory and retention policy.

`--tool-cleanup ask` is the default. After the operation, a terminal offers to remove picotool, its retained archive and support files only when the current run downloaded them. Previously retained packages are kept without a cleanup question. Without a terminal, the tool is kept. `--tool-cleanup keep` retains it without asking; `--tool-cleanup remove` explicitly requests removal of a managed package, including a retained one, without prompting. `--json-only` never asks questions; its default cleanup policy keeps the tool.

Cleanup removes only an unchanged installer-managed package. It never removes
an existing user-installed picotool, firmware backups or recovery records.
Unfinished operations, unreadable/unknown recovery records, changed package
files or added user files prevent removal. An unresolved transaction retains
its tool so the printed same-board continuation command remains usable.
Small private lock/state-index files remain for safe reuse and recovery checks.

Temporary bootstrap files and incomplete download staging are removed on normal
exit and handled interruptions. Cleanup failures are reported separately and
do not replace a verified firmware result. No cleanup operation erases or
changes the Pico's saved settings.

WsprryPi's imported installer entry does not download or remove tools. Fleet
continues to use its configured host executable and shared verification logic.
