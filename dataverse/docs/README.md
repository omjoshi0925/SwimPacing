# 200 Freestyle SCY Race Splits (Male, Pacific Swimming and CIF, 2021-2026)

## Summary
Race-level results for the men's 200 yard freestyle, short course yards,
compiled from publicly posted meet results for 16 meets held between
2021-10-23 and 2026-07-30. The dataset supports research on pacing
strategy: how swimmers distribute effort across the four 50 yard segments
of the race. 1,382 swims by 841 distinct swimmers.

## Files
- `races_200free_scy.csv` - the dataset, 1,382 rows by 18 columns.
- `codebook.csv` - variable name, type, units, and definition for every column.
- `prepare_deposit.py` - the script that produced the CSV from the author's
  working file, for provenance.

## Provenance
Records were transcribed by the author from publicly posted meet results
(SwimCloud event pages and Pacific Swimming meet result documents) saved
between 2026-08-31 and 2026-09-02. The `data_source` column records the
specific source and retrieval date for each row. Only factual competition
results are reproduced: times, splits, and meet identifiers. No source
page layout, text, or compilation is redistributed here.

## Inclusion criteria
- Event: 200 yard freestyle
- Course: short course yards (SCY)
- Sex category: male
- Meets: Pacific Swimming LSC meets and CIF sectional/state championships

## Structure and units
One row is one swim. A swimmer appearing in both a prelim and a final
contributes two rows, distinguished by `round`.

**Splits are cumulative, not per-segment.** `split_50` is elapsed time at
50 yards, `split_100` is elapsed time at 100 yards, and so on. `split_200`
equals `final_time`. To obtain segment times, difference consecutive
splits. `split_50` is stored in plain seconds; the remaining splits and
`final_time` are stored as mm:ss.hh strings.

## Known gaps
- Splits are present for 832 of 1,382 swims. Meets that published only
  final times contribute rows with `final_time` and no splits.
- `age` is present for 723 swims; `seed_time` for 193. Several sources
  published neither.
- `meet_date` is the meet's first day. For multi-day meets the specific
  swim day is usually unknown; affected rows say so in `notes`.
- Reaction times and 15 metre splits were not available from any source
  and are omitted entirely.
- Finishing place, where known, appears in the `notes` free text rather
  than a dedicated column.

## Privacy
Swimmer names, team affiliations, and USA Swimming identifiers are not
included. Each swimmer carries a pseudonymous `swimmer_id` that is stable
within this dataset and not linkable to any external identifier.

## License
CC0 1.0 Universal (public domain dedication).

## Citation
Joshi, O. (2026). 200 Freestyle SCY Race Splits (Male, Pacific Swimming
and CIF, 2021-2026). Harvard Dataverse. https://doi.org/10.7910/DVN/9N3Y2S

## Contact
Om Joshi. omjoshi823@gmail.com
