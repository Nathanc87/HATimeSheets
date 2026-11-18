## [0.1.63] - 2026-11-18

### Fixed
- Apply penalty rules according to the time-entry scope: Work rules apply to ordinary work and Travel rules apply to Work - Travel (overseas) entries.
- Preserve the separate Travelling checkbox behaviour, which remains capped at 10 paid hours and excluded from penalty rules.
- Add regression tests for Sunday work, Sunday Work - Travel and separate travelling entries.

## [0.1.62] - 2026-11-17

### Added
- Add an Estimated EOFY gross projection to the Financial Year overview.
- Project only future enabled roster days through 30 June using the configured shift times, breaks, pay-rate history, overtime tiers, penalties and allowances.
- Show actual gross YTD, projected remaining gross, projected allowances, rostered days and hours, and estimated EOFY gross.
- Keep all existing entries, settings and database records unchanged.

## [0.1.61] - 2026-11-17

### Changed
- Show a project or work-entry type between the date number and hours in each calendar day.
- Display Annual Leave, Sick Leave or Public Holiday in place of the project label when applicable; show Work - Travel for overseas work.
- Keep daily logged hours visible and show concise project labels when multiple projects are recorded.
- Bump add-on and static asset versions to 0.1.61.

## [0.1.60] - 2026-11-17

### Fixed
- Import datetime in the API module so new and edited shift entries can be rounded to 15-minute intervals without a NameError.
- Fixes the HTTP 500 response from POST /api/shifts when saving a new entry.

## [0.1.59] - 2026-11-17

### Changed
- Add Basic and Detailed modes to the Financial Year overview pie chart.
- Basic mode groups earnings into Work, Work - Travel, Annual Leave, Sick Leave and Public Holiday.
- Detailed mode retains the individual pay-code breakdown and allowances.
- Bump add-on and static asset versions to 0.1.59.

## [0.1.58] - 2026-11-17

### Changed
- Let the Reports table size the Hours by rate column automatically to fit the longest rate line.
- Keep each rate breakdown on a single line; the report table can scroll horizontally when required.
- Bump add-on and static asset versions to 0.1.58.

## [0.1.57] - 2026-11-17

### Fixed
- Default the Dashboard Selected dates chart to the most recently completed pay period, using the configured Cycle Anchor / First Day and cycle type.
- Exclude the Selected dates chart inputs from the generic today-date initializer so they are not pre-filled with today before pay-cycle defaults are applied.
- Preserve manually selected chart date ranges when the dashboard refreshes.
- Bump add-on and static asset versions to 0.1.57.

## [0.1.56] - 2026-11-17

### Changed
- Default the Reports date range to the most recently completed pay cycle using the configured Cycle Anchor / First Day and cycle type.
- For a Wednesday-to-Tuesday weekly cycle, select the prior Wednesday-to-Tuesday period from Wednesday through Tuesday, including Thursday payday.
- Keep manual date editing and previous/next pay-period navigation; use the configured overtime week start only as a fallback when no pay-cycle anchor is set.
- Bump add-on and static asset versions to 0.1.56.

## [0.1.55] - 2026-11-17

### Changed
- Refresh dashboard and report values immediately when Privacy Mode is toggled, without requiring page navigation.
- Keep earnings pie charts visible in Privacy Mode; hide currency amounts while retaining the percentage labels and chart proportions.
- Bump add-on and static asset versions to 0.1.55.

## [0.1.54] - 2026-11-17

### Changed
- Add Privacy Mode, enabled by default on every app load, with a header toggle to reveal or hide pay figures.
- Mask monetary amounts across dashboard charts, report totals and allowance tables while leaving hours and time entries visible.
- Conceal the hourly rate field in the pay-rate history editor while Privacy Mode is enabled.
- Bump static asset and add-on versions to 0.1.54.

## [0.1.53] - 2026-11-17

### Changed
- Reformat Excel export into a single Pay Summary worksheet with Earnings first and Allowances underneath.
- Use payslip-style columns for Description, Dates, Hours/Units, Rate, Amount, YTD Hours and YTD Amount.
- Group earnings by configured pay code and effective hourly rate, including separate travel and overtime cost codes.
- Calculate YTD figures from 1 July through the selected pay-period end date.
- Apply formatting, subtotals and a highlighted YTD Hours column.

## [0.1.52] - 2026-11-17

### Changed
- Replace the single base hourly rate with an editable pay-rate history using effective dates, initially dated 1 July 2026.
- Apply the rate effective on each shift/travel entry date when calculating earnings, preserving historical rates after future pay rises.
- Migrate an existing configured base rate to the 1 July 2026 entry; if no rate was configured, leave it blank.
- Keep pay-rate effective dates editable and validate dates/rates when settings are saved.

## [0.1.51] - 2026-11-17

### Changed
- Set the supplied ordinary overtime and travel tier descriptions, cost-code names, thresholds and multipliers as the built-in defaults.
- Preserve existing custom settings; migrate only matching legacy built-in tier descriptions to the new default wording.
- Confirm the 2026-27 resident tax brackets already match the supplied defaults.
- Update the Travelling note to: “(Travelling is 10hrs max per day with no penalties included)”.

## [0.1.50] - 2026-11-17

### Changed
- Rename the Overseas entry type to Work - Travel in the time-entry selector and payroll category descriptions while retaining the existing stored overseas flag and travel-tier calculations.
- Round saved shift clock-in times up to the next 15-minute interval and clock-out times down to the previous 15-minute interval. The API applies rounding on both create and edit so payroll and reports use the rounded times.

## [0.1.49] - 2026-11-17

### Changed
- Move Overseas and Public holiday from separate checkboxes into the Entry type dropdown alongside Work, Annual Leave and Sick Leave.
- Keep Overseas and Public holiday as work-hour entries; existing payroll flags and calculations remain unchanged.
- Preserve existing entries when editing by mapping their saved Overseas and Public holiday flags back to the corresponding dropdown option.

## [0.1.48] - 2026-11-17

### Fixed
- Correct the Settings page markup so Projects, Working Hours, Pay & Overtime, Travel & Overseas, and Public Holidays are sibling panels rather than nested inside Data & General.
- Restore each settings group's controls when its navigation tab is selected.

## [0.1.47] - 2026-11-17

### Changed
- Add a dedicated Projects page under Settings, separate from Data & General.
- Remove the separate Travel & Overseas Additional Multiplier setting; travel tier multipliers now define the complete rates for travel and overseas work.
- Apply configured travel tier thresholds, multipliers and cost-code names consistently to travelling entries, separate travel entries and overseas work.
- Retain the 10-hour paid cap for travelling entries and the 1.5× minimum for overseas hours after the first 10 paid hours.
- Ignore and remove the legacy additive loading value when loading existing settings, without changing saved project names or time entries.

## [0.1.46] - 2026-11-17

### Changed
- Reorganise Settings into Data & General, Working Hours, Pay & Overtime, Travel & Overseas, and Public Holidays subpages.
- Fix weekday names and their weekday indexes in the normal-hours roster; only enabled state and start / finish times are editable.
- Move overtime and travel cost-code names onto their corresponding tiers so each tier owns its label, threshold and multiplier.
- Migrate existing payroll-code labels onto the matching tiers without overwriting saved settings or historical time entries.
- Expose travel tiers in Settings and persist their cost-code names and multipliers.

## [0.1.45] - 2026-11-17

### Changed
- Remove the standalone New entry sidebar item; new entries can be started from the Time entries calendar.
- Add the configured allowance rate beside each allowance name in the report and CSV / Excel exports, before frequency.
- Add editable payroll-code labels in Payroll Settings for ordinary, overtime, public holiday, travel and leave codes.

## [0.1.44] - 2026-11-17

### Changed
- Place Time in and Time out side by side in the time-entry editor, with the unpaid break on its own row.
- Show the selected entry date in a long weekday format (for example, Tuesday, 29 October 2026) in the day-navigation toolbar.

## [0.1.43] - 2026-11-17

### Fixed
- Move previous / next day controls into a prominent, full-width toolbar directly above the entry form so they are visible while creating or editing entries.
- Add cache-busting version parameters to the app JavaScript and stylesheet to prevent Home Assistant ingress from continuing to serve stale assets.
- Display the currently selected entry date between the navigation controls and update the sidebar version label.

## [0.1.42] - 2026-11-17

### Added
- Add previous-day and next-day navigation to the time-entry editor. Existing entries for the selected day can be opened directly; days without an entry open a new dated form.
- Detect unsaved form changes and prompt to save before navigating, with an option to discard or cancel navigation. Failed saves keep the user on the current day.

## [0.1.41] - 2026-11-16

### Fixed
- Restore a usable Notes column width in the report after adding the Project column; widen the report table and wrap notes without breaking words mid-character.
- Give the Excel export Notes column a wider fixed width and enable text wrapping.

## [0.1.40] - 2026-11-16

### Fixed
- Complete project-filtered reporting so time entries and linked travel are recalculated only for the selected project, with generic allowances excluded from project-specific totals.
- Move project management into Payroll Settings and show project names in report rows.

## [0.1.39] - 2026-11-16

### Added
- Add reusable project names to time entries, with project management, project selection and report filtering.

## [0.1.38] - 2026-11-16

### Changed
- Calculate hourly allowances only on actual worked hours and separate travel hours; exclude public holiday, annual leave and sick leave entries.
- Apply the same eligible-hour rule to weekly PAYG gross allocation for hourly allowances.

## [0.1.37] - 2026-11-16

### Fixed
- Remove the duplicate legacy time-entry form submit handler that caused each calendar-created entry to be posted twice.

## [0.1.36] - 2026-11-16

### Fixed
- Prevent duplicate time-entry creation when the save action is triggered more than once before the first request completes.

## [0.1.35] - 2026-11-16

### Added
- Replace dashboard recent shifts with earnings breakdown pie charts for the current Australian financial year and a selectable date range, including allowances.
- Add Annual Leave and Sick Leave time-entry types, each recorded as 10 paid hours without requiring start, finish or break times.

## [0.1.34] - 2026-11-16

### Changed
- Rebalance timesheet report columns to give Hours by rate more width and wrap long rate labels cleanly without forcing narrow columns.

## [0.1.33] - 2026-11-16

### Changed
- Make calendar days clickable to edit an existing entry or create a new entry for that date.
- Display each hours-by-rate breakdown on its own line in reports.

## [0.1.32] - 2026-11-16

### Added
- Add a monthly hours calendar above the Time entries table, showing daily paid hours and highlighting past scheduled workdays with no recorded hours.

## [0.1.31] - 2026-11-16

### Fixed
- Use configured ATO weekly PAYG Scale 1 / Scale 2 coefficients in preference to annualised resident tax brackets. Weekly coefficients include the standard Medicare levy, correcting take-home estimates.
- Retain annual resident tax brackets as a fallback for financial years without weekly ATO coefficients.

## [0.1.30] - 2026-11-16

### Fixed
- Release the JavaScript navigation fix so Home Assistant detects an add-on update.

## [0.1.29] - 2026-11-16

### Changed
- Show overseas work entries as Work – Overseas in the time-entry list, reports and CSV / Excel exports.
- Add previous-week / next-week navigation to Reports & export, aligned with the configured overtime week.
- Replace weekly PAYG coefficient editing with annual Australian resident tax brackets by financial year. Weekly gross is annualised at 52 weeks, annual tax is calculated and divided by 52; Medicare levy is excluded.

## [0.1.28] - 2026-11-16

### Changed
- Replaced manual JSON editing of PAYG financial-year tables with a financial-year selector and visual Scale 1 / Scale 2 weekly bracket editors.
- Added controls to add financial years and withholding brackets, with validation for bracket limits and coefficients.

## [0.1.27] - 2026-11-16

### Fixed
- Start the application through the s6 `with-contenv` wrapper so Supervisor-provided environment variables, including `SUPERVISOR_TOKEN`, are available to the Home Assistant API integration.

## [0.1.26] - 2026-11-16

### Fixed
- Updated the sidebar version label to match the add-on release version.

## [0.1.25] - 2026-11-16

### Fixed
- Preserved Home Assistant entity-discovery errors in the Automatic attendance settings instead of overwriting them with the setup prompt.
- Displayed the API error detail returned by the backend so connection and permission failures can be diagnosed.

## [0.1.24] - 2026-11-16

### Fixed
- Enabled the Home Assistant Core API permission required by the presence entity and work-zone discovery endpoint.

## [0.1.23] - 2026-11-16

### Added
- Added configurable Home Assistant presence tracking with selectable person/device_tracker entities and multiple work zones.
- Automatically records one ordinary shift across work-zone changes, with a persisted grace window and finish time based on actual departure (rounded to the configured interval).
- Added Supervisor API entity discovery and persistent presence session recovery.

# Changelog

## [0.1.22] - 2026-11-16

### Changed
- Simplified the dashboard to show total paid work and travel hours, estimated gross and estimated take-home pay for the selected week.
- Added previous/next week navigation and a clear week-ending date label.


## [0.1.21] - 2026-11-16

### Changed
- Removed the detailed weekly withholding breakdown from the report summary; weekly PAYG still contributes to the period totals.
- Simplified allowance calculation bases to concise labels such as `Per Week`, `Per Shift` and `68.00 Hours`.


## [0.1.20] - 2026-11-16

### Fixed
- Updated payroll tests to expect the new reporting-only payroll-code metadata.

### Changed
- Removed the HELP / study-loan option from settings and exports; weekly PAYG remains income-tax withholding only.


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

## [0.1.15] - 2026-11-16

### Added
- Added weekly PAYG withholding estimates using the ATO 2026–27 Schedule 1 coefficients, with optional HELP withholding and extra weekly withholding.
- Added editable financial-year coefficient tables, tax-free threshold selection and weekly gross-to-net reporting.
- PAYG and estimated take-home amounts are included in CSV and Excel exports.

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
- Added this changelog to the add-on directory for Home Assistant release notes.

### Changed
- Removed the quick-entry form from the dashboard.
- Time entry editing now opens the dedicated entry page.
- Bumped the Home Assistant add-on and application version to 0.1.2.
