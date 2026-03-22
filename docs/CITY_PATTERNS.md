# DeltaScanner — City Patterns

Known data patterns across cities.

## Texas Pattern (tx_trw, tx_fixedwidth)
- Tax: Fixed-width tax roll files (TRW for Dallas, Master.dat for Fort Worth)
- CE: Socrata 311 (Dallas) or ArcGIS (Fort Worth)
- Join: Address-based (county accounts differ between tax and CE systems)
- Enrichment: SPTD/SPTB property type codes from tax data
- Cities: Dallas, Fort Worth, Houston

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
- Cannot meet intersection or tax >= 50% rules
- Temporary models until tax data arrives
- Cities: Philadelphia, Orlando
