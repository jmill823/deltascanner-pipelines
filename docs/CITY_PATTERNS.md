# DeltaScanner — City Patterns

Known data patterns across cities.

## Texas Pattern (tx_trw, tx_fixedwidth)
- Tax: Fixed-width tax roll files (TRW for Dallas, Master.dat for Fort Worth)
- CE: Socrata 311 (Dallas) or ArcGIS (Fort Worth)
- Join: Address-based (county accounts differ between tax and CE systems)
- Enrichment: SPTD/SPTB property type codes from tax data
- Cities: Dallas, Fort Worth, Houston
- **Houston staleness note:** Houston CE data is from Aug 2018 (7+ years stale).
  Config has `ce_data_stale: true` and `ce_data_date: "2018-08"`. V2 upgrade planned
  with fresh CE source. Scoring weights unchanged — CE downweighted to 25% total.

## Florida NAL Pattern (fl_nal)
- Parcel spine: FL DOR NAL file (statewide, filtered by CO_NO)
- Tax: County-specific PRR response or cert sale list
- CE: Varies (ArcGIS, Socrata, XLSX PRR)
- Join: Folio number (13-digit Miami-Dade, 12-digit Broward, 17-digit Palm Beach, 10-digit Duval)
- Enrichment: NAL provides property_type via DOR_UC, owner, address, assessed value
- Cities: Miami-Dade, Fort Lauderdale, Jacksonville, Orlando, Palm Beach

## Socrata + Parcel ID Pattern (socrata_parcelid)
- Both tax and CE available via Socrata API
- Join: Parcel ID (BBL for NYC, PIN for Chicago)
- Cities: NYC, Chicago

## Address-Only Pattern (address_only)
- Tax and CE parcel IDs are incompatible
- Join: Normalized address match
- Lowest match rates (typically 30-40%)
- Cities: Charlotte

## CE-Only Pattern (ce_only)
- Tax delinquency data not yet available (PRR pending)
- Config flag: `ce_only: true` — validator skips tax >= 50% and intersection checks
- Temporary models until tax data arrives
- Cities: Philadelphia, Orlando
