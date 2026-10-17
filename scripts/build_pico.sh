#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$project_root/scripts/xcode_env.sh"

if [[ -z "${PICO_SDK_PATH:-}" || ! -d "$PICO_SDK_PATH" ]]; then
  echo 'Set PICO_SDK_PATH to the pinned local Pico SDK 2.3.1 checkout.' >&2
  exit 1
fi

# The project pins picotool in CMake. Reuse an already populated local source
# tree as the local Git source, with private build outputs for this directory.
picotool_source="${PICOTOOL_FETCH_FROM_GIT_PATH:-$project_root/build/pico2-w/_deps}"
if [[ ! -d "$picotool_source/picotool-src" ]]; then
  echo "Set PICOTOOL_FETCH_FROM_GIT_PATH to a populated local picotool tree." >&2
  exit 1
fi

target="${1:-WsprryPico}"
case "$target" in
  WsprryPico) default_dir="$project_root/build/pico2-w-local" ;;
  WsprryPico-Inhibited) default_dir="$project_root/build/pico2-w-local-inhibited" ;;
  WsprryPico-StandaloneRF) default_dir="$project_root/build/pico2-w-local-standalone-rf" ;;
  *) echo 'Usage: build_pico.sh [WsprryPico|WsprryPico-Inhibited|WsprryPico-StandaloneRF] [build-directory]' >&2; exit 2 ;;
esac
if [[ $# -gt 2 ]]; then
  echo 'At most a target and build directory may be specified.' >&2
  exit 2
fi
build_dir="${2:-$default_dir}"
mkdir -p "$build_dir"
build_dir="$(cd "$build_dir" && pwd)"
cmake -S "$project_root" -B "$build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DWSPRRY_PICO_BUILD_FIRMWARE=ON \
  -DWSPRRY_PICO_BUILD_TESTS=OFF -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH="$build_dir/_deps" \
  -DPICOTOOL_GIT_REPOSITORY_URL="$picotool_source/picotool-src"
cmake --build "$build_dir" --target "$target" -j 4
