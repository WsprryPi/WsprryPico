#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="$project_root/build/host-debug"

source "$project_root/scripts/xcode_env.sh"
if [[ "$(uname -s)" == Darwin ]]; then
  build_dir="$project_root/build/host-xcode"
fi

cmake -S "$project_root" -B "$build_dir" -G Ninja \
  -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build "$build_dir"
ctest --test-dir "$build_dir" --output-on-failure
