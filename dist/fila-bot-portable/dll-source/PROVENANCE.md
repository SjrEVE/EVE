# DLL provenance

`src/eve-memory-reader.dll` — build từ source trong `dll-source/` (fork chengyus
của jamesalbert/eve-memory-reader, gốc: Sanderling line).

- Current SHA256 (build 2026-11-11): `796288f360385d93e0ea61eaeb43931a830d3d05c0a4a073d507bd2db33c756d`
  (bản trước `14bc2b56...` — giữ backup tại vendor/.../eve-memory-reader.dll.bak-14bc)

## Current build 2026-11-11 — cold-start scan

- Build: Zig 0.13.0 `cc -target x86_64-windows-gnu -O2 -DUNICODE -D_UNICODE -shared`
  with `cache.c eve-memory-reader.c hashtable.c memory.c process.c python.c uitree.c`
  and `-lpsapi -lkernel32 -luser32`.
- Cold-start trên client TQ thật: `initialize()` 8.813s; poll đầu 0.130s, 597 UI nodes;
  ba warm poll tiếp theo 0.080s, 0.077s, 0.079s. Read-only, không gửi input vào EVE.
- Không copy toàn bộ committed memory vào DLL: chỉ lưu metadata vùng, đọc từng vùng khi cần;
  tìm UIRoot type/instances trong MEM_PRIVATE, nhưng vẫn tìm metatype trên mọi vùng.
- Fix crash: `DICT_KEYS_OF_INTEREST` có NULL sentinel; kiểm tra NULL/size trước khi đọc buffer
  và trước `strcmp`; `FreeProcessSample` giải phóng metadata kể cả khi content NULL.
- Verification: live UIRoot/cold/warm probe PASS; `tests/run_all.py`: 549 PASS, 0 FAIL.

## Historical build 2026-11-09 chiều (2c199580)

5. **Decode Bunch** (`read_python_type_bunch` trước RỖNG): ground từ Sanderling
   `ReadingFromPythonType_Bunch` — Bunch là dict, chỉ giữ `htmlstr` (text của
   `SE_TextlineCore._sr`). DLL bỏ tag HTML + gộp khoảng trắng rồi cắt ≤3000 ký tự,
   emit `{"htmlstr":"..."}`. → đọc được nội dung offer agent (title, pickup, dropoff, cargo, reward).
6. **PyChildrenList**: `_childrenObjects` có thể là `PyChildrenList` → đọc thêm 1 tầng
   (Sanderling EveOnline64.cs ~975). Trước đây `ButtonGroup` trong AgentDialogueWindow = 0 con;
   nay thấy `AcceptMission_Button` / `DeclineMission_Button` / `DeferMission_Button`.
7. `uitree.c` + `cache.c`: in/copy `bunch_value` cho cả `is_bunch` (không chỉ PyColor).
   Verify client TQ 2026-11-09 (fixture `tests/fixtures/ui_tree_agent_offer.json`).
   Giới hạn biết trước: ký tự ngoài ASCII thành ' ' (vd `m³` → `m `).
- Build: mingw-w64 (w64devkit GCC 16.2.0), Release x64, ngày 2026-11-09
- Build lại: `bash dll-source/build_mingw.sh` (hoặc trỏ path tới gcc của w64devkit), hoặc MSVC:
  `msbuild eve-memory-reader.vcxproj /p:Configuration=Release /p:Platform=x64`
- Historical SHA256: `2c199580fcda860675175d4473d4c6948c6790c44dd67c4822e8f69511124265`.

## Thay đổi so với build 2026-11-07 (MSVC)

1. **Fix bug float (quan trọng):** `read_python_type_float()` trước đây là hàm RỖNG
   → mọi giá trị float trong UI tree trả `null` (HP gauge `_lastValue`, `_rotation`…).
   Nay đọc `PyFloatObject.ob_fval` (double tại +0x10); `FLOAT float_value` → `double`.
   → `ship_health()` đọc được shield/armor/structure thật.
2. Portability để build bằng mingw-w64: `MEMORY_BASIC_INFORMATION` thay `...64`,
   cast `LPCVOID`, include `<stdio.h>`, `return candidates` thay `return;` (hàm trả pointer),
   `wcstombs_s` dùng `size_t`, sửa `PyDictEntry**` trong `python.c`.
3. **Decode PyColor** (`read_python_type_pycolor`): ground từ Sanderling
   `implement/read-memory-64-bit/EveOnline64.cs` (`ReadingFromPythonType_PyColor`):
   PyColor +0x10 trỏ dict `{_a,_r,_g,_b}` → giá trị PyFloat 0..1 → emit JSON
   `{"aPercent","rPercent","gPercent","bPercent"}`. `uitree.c` in object JSON,
   `cache.c` copy `bunch_value`. → `Eye.capacitor_percent()` đọc được cap thật.
   Verify trên client TQ 2026-11-09: 39 màu khác nhau, 24 pmark `aPercent=0` (cap đầy → 100%).
4. Không đổi key nào trong `DICT_KEYS_OF_INTEREST` (vẫn 25 key như bản cũ).

## Chưa verify / chưa làm

- Cap ở trạng thái **CẠN MỘT PHẦN** chưa quan sát được (chưa có module tiêu cap / warp chưa
  kích hoạt thành công). Công thức `aPercent < 20 = đoạn còn` lấy từ Sanderling (2019) —
  cần 1 lần cap <100% trên Photon HUD để chốt ngưỡng. Fail-closed vẫn giữ: không màu → None.
