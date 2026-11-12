# MissionRunner V1 scope

Security L1, one character/client/agent/base/verified ship profile. Reuses the existing runner and shared perception/control.

Acceptance policy remains `non_anomic`; mission execution coverage and fire authorization are separate. No abandon or newly added decline policy; no account login, purchase or refit automation.

A profile is required before LIVE input. `config/security-profile.example.json` intentionally has null identity/build values: these are unknown, not safe defaults. CLI accepts `security --profile PATH`; actual data must be checked against the live client before operating.

Release requires the full plan's DoD: grounded capabilities, one full live mission, then three hands-off consecutive missions on a frozen build. Tests and replay do not certify live autonomy. The initial Foreign Investment snapshot is a resumed, already-running mission, NOT an autonomous cycle completed by this implementation.
