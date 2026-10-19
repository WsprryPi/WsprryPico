#!/usr/bin/env bash
# MIT. Bootstrap a single immutable installer revision; firmware defaults to main.
set -euo pipefail
if [[ "${EUID:-$(id -u)}" == 0 ]]; then
    echo 'Run this bootstrap as your ordinary user; scope USB permissions separately.' >&2
    exit 2
fi
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 2; }
command -v python3 >/dev/null || { echo 'Python 3.10 or newer is required.' >&2; exit 2; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 2)'
umask 077
installer_tmp=$(mktemp -d "${TMPDIR:-/tmp}/wsprrypico-usb.XXXXXXXX")
trap 'rm -rf -- "$installer_tmp"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
installer_revision=${WSPRRY_PICO_USB_INSTALLER_REVISION:-}
if [[ -z "$installer_revision" ]]; then
    curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --connect-timeout 10 --max-time 30 --max-filesize 1048576 \
        https://api.github.com/repos/WsprryPi/WsprryPico/commits/devel > "$installer_tmp/revision.json"
    installer_revision=$(python3 -c 'import json,re,sys; v=json.load(open(sys.argv[1]))["sha"]; assert re.fullmatch("[0-9a-f]{40}",v); print(v)' "$installer_tmp/revision.json")
fi
if [[ ! "$installer_revision" =~ ^[0-9a-f]{40}$ ]]; then
    echo 'Installer revision must be a full lowercase Git commit SHA.' >&2
    exit 2
fi
mkdir -p "$installer_tmp/scripts/ci"
for installer_file in scripts/usb_installer.py scripts/ci/release-manifest-1.schema.json; do
    curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --connect-timeout 10 --max-time 60 --max-filesize 1048576 \
        "https://raw.githubusercontent.com/WsprryPi/WsprryPico/$installer_revision/$installer_file" \
        > "$installer_tmp/$installer_file"
done
echo "WsprryPico installer source: $installer_revision" >&2
if [[ $# == 0 ]]; then set -- discover; fi
WSPRRY_PICO_USB_INSTALLER_REVISION="$installer_revision" python3 "$installer_tmp/scripts/usb_installer.py" "$@"
