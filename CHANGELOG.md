# Changelog

All notable changes to HATimeSheets are documented here.

## [0.1.5] - 2026-11-16

### Changed
- Exposed the travel pay multiplier as a direct setting, matching the capped travel-entry pay rule rather than exposing legacy travel tiers.
- Applied the configured travel multiplier to travel time entries; the 10-hour cap and exclusion from weekly overtime remain in place.

### Fixed
- Corrected the Excel export's elapsed-hours calculation to use time-in followed by time-out.

## [0.1.4] - 2026-11-16

### Added
- Added editable travel rate tiers to Payroll Settings, including thresholds and decimal multipliers.
- Added per-day rate category/hour breakdowns to the timesheet report and exports.
- Moved allowances before the period totals so totals appear at the bottom of the report.
- Added a totals breakdown by ordinary, overtime and penalty category to the CSV and Excel exports.

### Fixed
- Travel rate tiers are now loaded into the settings editor and saved back to payroll settings.

## [0.1.3] - 2026-11-16

### Fixed
- Changed numeric rule inputs to accept decimal increments, so penalty and overtime multipliers such as 1.5 can be entered.

## [0.1.2] - 2026-11-16

### Added
- Added a dedicated New Entry page for creating and editing time entries, separate from the dashboard.
- Added a daily timesheet report with date, time in, time out, unpaid break, paid hours, entry type and notes.
- Added a separate allowances section with frequency, calculation basis and amount.
- Restructured CSV and Excel exports to use a daily timesheet layout, with allowances itemised separately.
- Added this changelog to track future releases.

### Changed
- Removed the quick-entry form from the dashboard.
- Time entry editing now opens the dedicated entry page.
- Bumped the Home Assistant add-on and application version to 0.1.2.
