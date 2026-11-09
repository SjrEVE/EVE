#!/usr/bin/env bash
# Build eve-memory-reader.dll bằng mingw-w64 (w64devkit) — không cần MSVC.
#   tải w64devkit: https://github.com/skeeto/w64devkit/releases (giải nén, thêm bin vào PATH)
#   chạy: bash build_mingw.sh [đường-dẫn-gcc]   (mặc định: gcc)
# Verify hash sau khi build: xem PROVENANCE.md
set -euo pipefail
GCC="${1:-gcc}"
cd "$(dirname "$0")"
"$GCC" -O2 -DUNICODE -D_UNICODE -shared \
  -o eve-memory-reader.dll \
  eve-memory-reader.c cache.c hashtable.c memory.c process.c python.c uitree.c \
  -lpsapi -static-libgcc
echo "built: $(pwd)/eve-memory-reader.dll"
sha256sum eve-memory-reader.dll
