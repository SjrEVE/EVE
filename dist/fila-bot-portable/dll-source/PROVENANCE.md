# DLL provenance

`src/eve-memory-reader.dll` — build từ source trong `dll-source/` (fork chengyus
của jamesalbert/eve-memory-reader, gốc: Sanderling line).

- SHA256: `9f540a59a6f9425a860e2e2d7c1cb2c56e96d0faf0b3a876959ed294e9862eb5`
- Build: MSBuild VS2022 BuildTools, Release x64, ngày 2026-11-07
- Build lại: mở `eve-memory-reader.sln` từ repo gốc + source này, hoặc:
  `msbuild eve-memory-reader.vcxproj /p:Configuration=Release /p:Platform=x64`
- Verify: `sha256sum eve-memory-reader.dll` khớp hash trên; không khớp = KHÔNG dùng
