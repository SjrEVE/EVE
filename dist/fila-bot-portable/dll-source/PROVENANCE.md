# DLL provenance

`src/eve-memory-reader.dll` — build từ source trong `dll-source/` (fork chengyus
của jamesalbert/eve-memory-reader, gốc: Sanderling line).

- SHA256: `058616dfad29ddc49cde58b25be710d61cc6c254e365bf8f0f01797bb71fba83`
- Build: mingw-w64 (w64devkit GCC 16.2.0), Release x64, ngày 2026-11-09
- Build lại: `bash dll-source/build_mingw.sh` (hoặc trỏ path tới gcc của w64devkit), hoặc MSVC:
  `msbuild eve-memory-reader.vcxproj /p:Configuration=Release /p:Platform=x64`
- Verify: `sha256sum eve-memory-reader.dll` khớp hash trên; không khớp = KHÔNG dùng

## Thay đổi so với build 2026-11-07 (MSVC)

1. **Fix bug float (quan trọng):** `read_python_type_float()` trước đây là hàm RỖNG
   → mọi giá trị float trong UI tree trả `null` (HP gauge `_lastValue`, `_rotation`…).
   Nay đọc `PyFloatObject.ob_fval` (double tại +0x10); `FLOAT float_value` → `double`.
   → `ship_health()` đọc được shield/armor/structure thật.
2. Portability để build bằng mingw-w64: `MEMORY_BASIC_INFORMATION` thay `...64`,
   cast `LPCVOID`, include `<stdio.h>`, `return candidates` thay `return;` (hàm trả pointer),
   `wcstombs_s` dùng `size_t`, sửa `PyDictEntry**` trong `python.c`.
3. Không đổi key nào trong `DICT_KEYS_OF_INTEREST` (vẫn 25 key như bản cũ).

## Chưa decode được

- `PyColor` (pmark `_color`) — cap % vẫn unknown (`Eye.capacitor_percent()` trả None).
- `Bunch` — chưa parse (không dùng tới).
