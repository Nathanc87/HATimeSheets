# Changelog

## [0.1.19] - 2026-11-16

### Changed
- Aligned report hour totals with payroll codes, combining travel and overseas hours under the matching Travel-OTH code while preserving the underlying multipliers.
- Stacked period summary tables vertically at full report width for consistent alignment.
- Removed the HELP / study-loan line from the report summary.

## [0.1.18] - 2026-11-16

### Changed
- Render report totals as compact tables matching the existing timesheet and allowances list style.
- Group paid hours by category, allowances and gross earnings, and PAYG deductions and take-home pay.

## [0.1.17] - 2026-11-16

### Changed
- Reorganised report totals into compact vertical sections for paid hours by rate, allowances and earnings, and tax and take-home pay.
- Reduced summary typography and clarified weekly withholding rows.

## [0.1.16] - 2026-11-16

### Fixed
- Corrected newline formatting in the PAYG CSV and Excel export additions so the application compiles.

All notable changes to HATimeSheets are documented here.

## [0.1.14] - 2026-11-16

### Fixed
- Hourly allowances now include payable travel hours as well as ordinary work hours. The allowance basis shows the combined hours.

## [0.1.13] - 2026-11-16

### Changed
- Overseas work now ignores the normal-hours roster and uses a 10-hour daily ordinary threshold. The first 10 hours pay at the applicable weekly rate plus the overseas loading; hours after 10 attract at least the 1.5x overtime rate plus loading. Weekly overtime tiers still apply after their configured thresholds.

## [0.1.12] - 2026-11-16

### Changed
- Overseas time entries now use the `Overseas` pay category label instead of `Out-of-hours` or the underlying weekly tier label, while retaining the calculated multiplier.

## [0.1.11] - 2026-11-16

### Fixed
- Prevented weekday roster rows from being removed, keeping the seven weekday-to-index mappings stable; days can be disabled instead.

## [0.1.10] - 2026-11-16

### Fixed
- Corrected the weekday roster editor to retain the weekday index and expose only the roster start and finish times; actual unpaid breaks remain recorded on each shift.

## [0.1.9] - 2026-11-16

### Fixed
- Saved weekday roster rules with their stable weekday index so the configured schedule is applied to the correct day.
- Removed the unused roster-level break field; unpaid breaks remain defined per time entry.


## [0.1.8] - 2026-11-16

### Fixed
- Preserved each weekday's identifier when saving the normal-hours roster, ensuring the payroll engine matches the configured day correctly.
- Removed an unused roster break field; actual unpaid breaks continue to come from each time entry.
## [0.1.7] - 2026-11-16

### Added
- Added the daily roster editor to Payroll Settings, including enabled days, start/finish times and unpaid break settings.
- Added the additive travel/overseas loading control to Payroll Settings.

### Fixed
- Updated legacy default overtime bands to the new four-band defaults while preserving custom existing tiers.
- Updated the overseas-loading payroll test to reflect the new +0.3x rule.

\n## [0.1.6] - 2026-11-16

### Added
- Added editable normal working hours for each day, including enabled days, start/finish times and unpaid break settings.
- Work outside the configured daily roster now attracts at least 1.5× pay, regardless of weekly hours.
- Added editable default weekly pay bands: 1.0× through 38 hours, 1.5× from 38–40, 1.5× from 40–44, and 2.0× above 44.
- Added configurable additive travel/overseas loading, defaulting to +0.3× on the applicable rate.

### Changed
- Existing installations inherit newly introduced defaults without overwriting their saved settings.

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
