#!/usr/bin/env bash
# Source this from repository checks that spawn host compiler subprocesses.
if [[ "$(uname -s)" == Darwin ]]; then
  developer_dir="$(xcode-select -p 2>/dev/null || true)"
  if [[ "$developer_dir" != *"/Xcode.app/Contents/Developer" ]]; then
    developer_dir=/Applications/Xcode.app/Contents/Developer
  fi
  if [[ ! -d "$developer_dir/Platforms/MacOSX.platform/Developer/SDKs" ]]; then
    echo "Full Xcode is required for this Mac: $developer_dir" >&2
    return 1
  fi
  export DEVELOPER_DIR="$developer_dir"
  export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
  export CC="$(xcrun --sdk macosx --find clang)"
  export CXX="$(xcrun --sdk macosx --find clang++)"
fi
