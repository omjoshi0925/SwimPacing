# Pre-registration provenance

Git history is this study's pre-registration record. The validation plan was
committed before any calibration or test-set use; later changes to it are
bracketed amendments in the file, each with its own commit; the dataset freeze
and the registered run have their own commits. The tables below are generated
from `git log`, newest first, so the ordering can be checked without trusting
prose. Verify a row with `git show <hash>:docs/validation_plan.md` or
`git show --stat <hash>`. A Zenodo DOI minted from a GitHub release of a
tagged commit would add a third-party timestamp; until then these hashes are
the reference.

## docs/validation_plan.md, every commit

`git log --format='%h %ad %s' --date=iso-strict -- docs/validation_plan.md`

| hash | author date | subject |
|---|---|---|
| 063dd1b | 2026-09-06T16:57:29-07:00 | docs(plan): declare the band K per-race start-credit analysis exploratory, dated before the run (row 110) |
| 88de8d9 | 2026-09-02T20:17:20-07:00 | feat(validation): freeze pilot-v0.2, run the registered held-out analysis, and draft the paper |
| af07cd9 | 2026-09-02T15:48:01-07:00 | feat(data): two meets ingested via new parsers and club-linked age rule |
| 8878760 | 2026-09-01T12:39:32-07:00 | docs(plan): declare the exploratory pilot fits |
| d7767c7 | 2026-09-01T12:35:04-07:00 | docs(plan): log start-transform amendment, extend credit band to 3.4 s |
| 640ada6 | 2026-08-31T19:12:31-07:00 | Pilot empirical validation: 80 real races, M0-M4 comparison |

## data/DATASET_VERSIONS.md, every commit

`git log --format='%h %ad %s' --date=iso-strict -- data/DATASET_VERSIONS.md`

| hash | author date | subject |
|---|---|---|
| 88de8d9 | 2026-09-02T20:17:20-07:00 | feat(validation): freeze pilot-v0.2, run the registered held-out analysis, and draft the paper |
| bccb4db | 2026-09-02T17:05:17-07:00 | feat(data): splitless-source support; BAC 2021 PB-history rows; manifest |
| af07cd9 | 2026-09-02T15:48:01-07:00 | feat(data): two meets ingested via new parsers and club-linked age rule |
| 8958ce4 | 2026-09-02T12:03:52-07:00 | feat(ingest): publish source sha256 digests without publishing sources |
| 640ada6 | 2026-08-31T19:12:31-07:00 | Pilot empirical validation: 80 real races, M0-M4 comparison |

## Fit and validation result commits

`git log --format='%h %ad %s' --date=iso-strict -- results/model_calibration results/validation`

| hash | author date | subject |
|---|---|---|
| 9f8fc1f | 2026-09-07T00:29:22-07:00 | docs(validation): record the M4 re-solve drift across the band K grid |
| 64eb776 | 2026-09-06T23:44:25-07:00 | docs(validation): report exploratory per-race start credit S(v) = 15/v − t15 |
| c7219df | 2026-09-06T18:46:14-07:00 | results(validation): complete the band K sweep, ten cells, and figure emp09 (row 112) |
| 7b9dede | 2026-09-06T17:00:59-07:00 | results(validation): exploratory per-race start credit S(v) |
| 88de8d9 | 2026-09-02T20:17:20-07:00 | feat(validation): freeze pilot-v0.2, run the registered held-out analysis, and draft the paper |
| 5eb1a0a | 2026-09-01T12:38:51-07:00 | results: pilot report gains the exploratory-fit section |
| 1b8fe76 | 2026-09-01T12:38:39-07:00 | feat(analysis): fitted-shapes figure and start-credit confound sweep |
| 2647efd | 2026-09-01T12:38:25-07:00 | results: exploratory train-only fits for beta_x, gamma, beta_E (pilot-v0.1) |
| d7767c7 | 2026-09-01T12:35:04-07:00 | docs(plan): log start-transform amendment, extend credit band to 3.4 s |
| 042dc2a | 2026-09-01T12:34:30-07:00 | fix(analysis): regenerate pilot comparison in the corrected space |
| 640ada6 | 2026-08-31T19:12:31-07:00 | Pilot empirical validation: 80 real races, M0-M4 comparison |
