# OPPORTUNITIES (JobBoard / Freelance Jobs) — trang thai & ke hoach

> Nguon: user bao "Game co cai opportunities rat de de lam mission" (2026-11-10).
> Panel do = **AIR Career Program** (Neocom ben le) -> mở **JobBoardWindow** co tab
> Freelance Jobs / Agent Missions. Co bon "Stats Jobs Accepted 0/3" — toi da 3 job dong thoi.

## Ground duoc xac nhan (khoang 18:00 ngay 2026-11-10, live TQ client)

Tinh bon struct doc duoc TRUC TIEP tu memory (dumps/g8_freelance.json, tests/fixtures/ui_tree_freelance_jobs.json):

- Neocom -> `airCareerProgram` (`_name="airCareerProgram"`, abs (16,112), text ngan khong doc duoc nhung _name la duy nhat)
- bam no -> `JobBoardWindow` mở (hoac bam ca 2: AIR + side tab `feature_agent_missions_entry` (281,167) de vao trang 'Agent Missions'
- JobBoardWindow > content_container > FreelanceProjectsFeaturePage > main_container > scroll_container...
	- `FeaturePageSummaryBar` — 3 SummaryStat(+Icon): `valueLabel` + EveLabelLarge
		- "Jobs Available" (valueLabel: 0)
		- "Corporations"     (valueLabel: 0)
		- "Jobs Accepted"    (valueLabel: 0/3)
	- `PageFilters` — 'Sort By', 'Filters', 'SingleLineEditText' (Search), + `TextHeader "0 Opportunities"`
	- `CardsContainer` > cac `FreelanceProjectCard name="entry_freelance_projects:<uuid>"` (job corp do)
		- `Container middle` > `TextHeader` — noi dung client (vi du "Sell me your Kernite, no risky travel to hubs/taxes/brokers")
		- `Container topCont` > `Container headerRow` > `titleCont` > `TextBody _name="top_title"` — ten job ngan
		- `Container topCont` > `SolarSystemChip`:
			- `TextDetail _name="locationName"` — he sao dia diem giao (Akiainavas / Ruvas)
			- `TextDetail _name="securityStatus"` — sec cua he     (0.7 / 0.8)
			- `TextDetail _name="jumps/numJumps"` — khoang cach lon  (matrixtu dump: sach chua thay nen None)
			- `TextDetail _name="numJumps"` — jump tu diem vo hang
		- Sinh vien card co `CorpColorBanner`, `CorpIcon`, `TagIcon`, `TimeRemainingIcon`...

## Da lam trong vong nay

1. `src/fila_bot/opportunities.py` — parser: `parse_jobboard(root)` → `{opened, summary, jobs[uuid,title,header,system,sec,jumps], ...}`, `format_summary()`; 17 unit test (tests/test_opportunities_parse.py, khong pytest) tren fixture dump that.
2. `python -m fila_bot.cli opportunities [--open] [--out path.json]` — doc (mac dinh) hoac bam airCareerProgram de mo, in/format JSON.
3. **DLL eve-memory-reader** xay lai O2 voi pan ca 4 bug NULL-deref doc UI tree (trai tim bot):
	- `bytes_array_contains` dem sentinel tren `NULL`/`size==0` → dong lo[np tu] khi wrong — da them `NULL`/`size` guard + `i != size - 1` (truoc la so sanh `!= bytes-1` nham con tro!)
	- `name_bytes == NULL` trong type-object reader → guard + free + return NULL
	- `key_string == NULL` trong 2 vong lap dict → `strcmp(non-null, NULL)` = crash (MSV C TRT ko validate) → guard `continue`
	- `python_object_type_name == NULL` trong 2 so sanh strcmp → guard
4. DLL copy sang `vendor/eve-memory-reader/x64/Release/eve-memory-reader.dll` (trung lap file `.bak-14bc`).
5. UI tree doc qua **0.22 giay moi lan refresh** (cho ~1M heap buffer) cho client that va agar d OSD; khong crash ca khi JobBoardWindow mo.

## Cau hoi con trong (khi user log client lai)

- [ ] Qua nhap panel 'Agents' trang Agent Missions chi ra gi: lay dump moi — dump card agent mission (giong FreelanceProjectCard hay khac) — cai nay moi la "mission" thuc su.
- [ ] Click vao 1 FreelanceProjectCard → cua so chi tiet — `Accept` button la type gi (`Button`/`ButtonIcon`), text label gi, `_name` gi?
- [ ] Bam 'Accept' → job di dau? (inventory? journal? mission list?) — bot can convert toi dieu kien 'fill pickup/dropoff'
- [ ] `numJumps` o dump bi None — sua parser doc dung ten.
- [ ] Neu job freelancer la NHAN VAT do corp cua boss (endpoint?), bot khong nên bam — fail-closed buoc user chi dinh.

## Dong bo voi Distribution/Courier mode (da co san)

- Mission list tu Opportunities → cac 'pick up System A → drop off System B' giong Distribution Courier: bot dung mode distribution hien co (set destination, undock/jump/dock, load cargo, complete) — chi can them `opportunities accept` connector: tu card → job dialog → 'Accept' → set destination → mode distribution follow.
