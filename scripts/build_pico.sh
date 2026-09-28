#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$project_root/scripts/xcode_env.sh"

if [[ -z "${PICO_SDK_PATH:-}" || ! -d "$PICO_SDK_PATH" ]]; then
  echo 'Set PICO_SDK_PATH to the pinned local Pico SDK 2.3.1 checkout.' >&2
  exit 1
fi

# The project pins picotool in CMake. Reuse an already populated local source
# tree so a build never needs a network fetch.
picotool_source="${PICOTOOL_FETCH_FROM_GIT_PATH:-$project_root/build/pico2-w/_deps}"
if [[ ! -d "$picotool_source/picotool-src" ]]; then
  echo "Set PICOTOOL_FETCH_FROM_GIT_PATH to a populated local picotool tree." >&2
  exit 1
fi

build_dir="$project_root/build/pico2-w-local"
cmake -S "$project_root" -B "$build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DWSPRRY_PICO_BUILD_FIRMWARE=ON \
  -DWSPRRY_PICO_BUILD_TESTS=OFF -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH="$picotool_source"
cmake --build "$build_dir" --target WsprryPico -j 4
