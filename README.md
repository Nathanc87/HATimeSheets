# HATimeSheets

A single-user Home Assistant add-on for recording shifts, travel, notes and configurable payroll calculations.

## Features
- Manual shift entry with start, finish and unpaid breaks
- Travel entries linked to a shift or recorded independently
- Shift notes and editable historical records
- Configurable base hourly rate (intentionally unset on first install)
- Configurable pay cycle and cycle anchor date
- Configurable overtime thresholds and multipliers
- Configurable day, time, public-holiday and travel penalty rules
- Hourly and fixed allowances
- Pay-period summaries and CSV / Excel exports
- Persistent SQLite database in the add-on `/data` directory

## Install in Home Assistant
1. Open **Settings → Add-ons → Add-on Store**.
2. Open the three-dot menu and select **Repositories**.
3. Add `https://github.com/Nathanc87/HATimeSheets`.
4. Find **HATimeSheets**, install it, then start it.
5. Open the add-on using **Open Web UI**.

The add-on uses Home Assistant Ingress. No external port or login is required.

## First setup
Open **Settings** in HATimeSheets and configure:
- Base hourly rate (leave blank until known)
- Pay cycle type and start date
- Week start day and ordinary-hours threshold
- Overtime tiers and penalty rules
- Travel rules and allowances

The initial rule set reflects the example discussed during development (38 ordinary hours, 1.5x from 38–44, 2x above 44, Sunday 2x, travel 1.3x / 1.8x / 2.3x). These are editable starting rules, not a verification of an award or enterprise agreement. Review them against your employment instrument before relying on estimated pay.

## Data and backups
All records are stored in `/data/timesheets.db`. Back up the Home Assistant add-on data regularly. CSV and XLSX exports are available from Reports.

## Development
The application is a FastAPI service with a SQLite database and a browser-based interface. Payroll rules are stored as data rather than hard-coded into the UI.

## Important
HATimeSheets is a personal record-keeping and estimation tool. It is not payroll software and does not determine legal award entitlements. Verify calculations against your employment agreement and payslips.