# Data availability

What race data this project rests on, where a citable copy of it lives, what
is withheld and why, and how anyone can verify that the numbers in the
repository were built from the official results. Written 2026-09-22 from the
deposit package in `dataverse/` (commit `35ad2f0`) and the published
Dataverse record.

## What is deposited

**Persistent identifier.** `https://doi.org/10.7910/DVN/9N3Y2S`, Harvard
Dataverse, version 1.0, published 2026-09-10 (deposited 2026-09-08). The
record was read through the Dataverse API on 2026-09-19 and again on
2026-09-22: state RELEASED, every file unrestricted.

**Title, as deposited.** *200 Freestyle SCY Race Splits (Male, Pacific
Swimming and CIF, 2021-2026).*

**Files.** Four, mirrored under `dataverse/` in this repository:

| deposited file | repository copy | what it is |
|---|---|---|
| `races_200free_scy.csv` (shown by Dataverse as `races_200free_scy.tab` after tabular ingest; original 761,554 bytes) | `dataverse/data/races_200free_scy.csv` | the dataset, 1,382 rows x 18 columns |
| `codebook.csv` | `dataverse/docs/codebook.csv` | name, type, units and definition of every column |
| `prepare_deposit.py` | `dataverse/code/prepare_deposit.py` | the script that produced the CSV from the working raw file |
| `README.md` | `dataverse/docs/README.md` | provenance, inclusion criteria, split convention, known gaps, license, citation |

The dataset, codebook and script in the repository are byte-identical to the
deposited files (the MD5 digests Dataverse lists match). The repository's
`README.md` differs from the deposited one by 15 bytes (2,840 against 2,825
bytes); the deposited text is the one that governs the record.

**Contents.** One row per swim: 1,382 swims by 841 pseudonymous swimmers at
16 meets between 2021-10-23 and 2026-07-30, men's 200 yard freestyle, short
course yards. Cumulative splits are present for 832 swims, a published age for
723, a seed time for 193. `data_source` records the source page or document
and the retrieval date for every row; `notes` carries meet dates, venue,
finishing place where known, and per-row caveats.

**Relation to the frozen dataset.** The deposited CSV is the frozen
pilot-v0.2 raw file (`data/raw/200_free_scy_raw.csv`, sha256 `00f67f24…`,
`data/DATASET_VERSIONS.md`) with four columns removed: `team`, and the three
columns that are empty in every row (`pre_race_pb`, `split_15m`,
`reaction_time`). Re-deriving it that way from the frozen raw file reproduces
the deposited CSV byte for byte (checked 2026-09-19).

## Access terms

From the deposit's own README, verbatim:

> CC0 1.0 Universal (public domain dedication).

No other terms apply. The Dataverse record carries the same license and lists
all four files as unrestricted.

## How to cite the data

From the deposit's own README, verbatim:

> Joshi, O. (2026). 200 Freestyle SCY Race Splits (Male, Pacific Swimming
> and CIF, 2021-2026). Harvard Dataverse. https://doi.org/10.7910/DVN/9N3Y2S

## What is not redistributed, and why

The population is male swimmers aged 15-18. Individual race rows as they
appear in the source results — name, club, age and time together — are
derived from publicly posted meet results but are not redistributed here,
in the repository or in the deposit, because that combination re-identifies
minors. The repository carries pseudonymous swimmer IDs in place of names
(`S###`, assigned at ingest, stable within the dataset; the identity map
lives in `data/private/` and is never published), no club affiliation in
anything it tracks, the sha256 digests of every source file and of the
frozen raw and processed files in `data/DATASET_VERSIONS.md`, and the digest
test described below, so anyone who re-collects the sources can verify the
reconstruction.

Concretely, three things stay out of the repository:

- the verbatim source files (official result sections and documents, with
  names) under `data/private/`, gitignored;
- the identity map from names to `S###` identifiers, in the same directory;
- `data/raw/` and `data/processed/`, gitignored, because the raw file carries
  the club column the deposit drops and the processed file is derived from it.

## Verification path

The public integrity record (roadmap row 037, `8958ce4`) makes the chain from
official results to every committed number checkable without any private
file changing hands.

1. **Sources.** `data/DATASET_VERSIONS.md`, "Source integrity", lists the
   sha256 of every private source file per meet. Anyone who re-retrieves the
   official page or document and saves the same section can confirm the
   dataset was built from the genuine file.
2. **Frozen files.** The same register records the frozen pilot-v0.2 raw file
   (sha256 `00f67f24c9f446ff256b40281b569a739618b1cdf707f1482d81952fad7e21c3`)
   and the processed file the registered analysis read
   (sha256 `c2a1929a3ea5f5308e833696775e7c53b03b597fffbdd0374cc1c6b85f433d6b`).
3. **The digest test.** The frozen processed digest is reproducible from the
   raw sources by the pipeline at HEAD:
   `tests/test_pipeline.py::test_frozen_dataset_regenerates_from_raw_at_the_register_digest`
   regenerates the processed file from the raw file into a temporary path and
   asserts its sha256 equals the digest read from the register (both digests
   are parsed from the register, not written into the test). It carries the
   `requires_data` marker, so it runs only where `data/` is present; it passes
   at HEAD, and it fails against the pipeline as it stood from `be0e710` to
   `5d133ef`, when a re-associated subtraction in one derived column moved the
   digest (repaired in `618b728`).
4. **From the deposit.** Adding the four dropped columns back, empty, in the
   raw column order and running `python -m src.preprocessing` on the result
   reproduces every column of the registered processed file except `team`,
   including the 345 usable races and the `P{i}_corrected` shares that the
   registered fits and the held-out comparison read (checked 2026-09-22).
   The registered digest itself needs the raw file, whose only additional
   content is the club column.
5. **Downstream.** The registered fits
   (`results/model_calibration/fits_train_v0_2.csv`) and the held-out
   comparison (`results/validation/model_comparison.csv`,
   `report_v0_2.md`) are committed next to the code that produced them;
   `docs/preregistration_provenance.md` gives the commit history that orders
   the plan, the freeze and the run.

## Code

The model, pipeline, calibration and evaluation code, the pre-registered
plan with its amendment log, the figures and the paper source are in this
repository under the MIT license (`LICENSE`, `CITATION.cff`). A `.zenodo.json`
is in place for a code DOI, to be minted from the first tagged release; until
then the commit hashes in `docs/preregistration_provenance.md` are the
reference.
