# Changelog

All notable changes to Scomp are documented in this file.

## [1.4.0] - 2026-10-29

### Changed

- Harmonized the TacticalData and PhysicalData dashboard headings, KPI cards, and responsive layout.
- Replaced the TacticalData competition list with recent scrape activity showing competition names and timestamps; removed decorative KPI circles.

## [1.3.0] - 2026-10-28

### Added

- User authentication with username and password sessions.
- Separate TacticalData and STATSport permissions, with full access for administrators.
- Administrator user management for account creation and access assignment.
- One-time account activation and password modification links.
- Scomp ETL login screen aligned with the shared interface rules and Kapture reference proportions.
- Initial administrator configuration through environment variables.

### Security

- Passwords are stored using `scrypt` hashes.
- Protected TacticalData and STATSport API routes now reject unauthenticated or unauthorized requests.
- Authentication sessions and one-time password tokens are stored as hashes.

## [1.2.0] - 2026-10-13

### Added

- Grouped Round scraping parser selections into Lineups, Periods/score/phases, Distances, Events, and Fitness runs.
- Expanded RGD persistence for phases of play, types of play, and collective and individual possessions.

### Changed

- Scoped parser processing and cleanup so each selected parser group handles only its own data.
- Updated scraping workflow and database view documentation.

### Fixed

- Aligned Fitness entity ORM identifiers with the existing `VARCHAR(50)` database columns to prevent PostgreSQL UUID/VARCHAR comparison errors.

## [1.1.2] - 2026-10-05

### Changed

- Activity now loads sessions month by month and refreshes the calendar when navigating between months.
- Added server-side date range filtering for PhysicalData sessions.
- Updated Activity calendar navigation and today highlighting to use the PhysicalData red accent.
- Improved squad display support through editable squad names in Settings.

## [1.1.0] - 2026-09-24

STATSports physical data provider and frontend architecture update.

### Added

- STATSports physical data pipeline with sessions, activities, players, squads, seasons, scraping logs, and automation rules.
- STATSports API routes for physical data, scraping, automation, logs, and catalog management.
- Independent STATSports frontend pages for overview, activity, scraping, players, automation, logs, and settings.
- STATSports activity calendar with squad colors and configurable season boundaries.
- Custom Scomp logo support through `frontend/public/image/logo.png`.

### Changed

- Organized backend and frontend code by provider while preserving existing SportsDynamics routes and behavior.
- Rebuilt the production frontend Docker image to serve the new logo asset.

### Database

- Added Alembic migrations for STATSports physical data, change tracking, scraping logs, seasons, and automation rules.

## [1.0.0] - 2026-09-21

First production release prepared for deployment.

### Added

- Task Center with task history, progress tracking, round information, task IDs, logs, and match statistics.
- Manual cooperative task cancellation from the task list.
- Settings page for competition and season configuration.
- Teams page with provider information.
- Task progress updates after each processed, skipped, or failed match.
- Celery reliability settings with late acknowledgements and single-task prefetching.
- Alembic merge migration consolidating the existing migration heads.
- Scraping task tracking with workflow, round, phase, current match, and error details.
- Production deployment configuration with shared dev/prod naming and centralized ignored configuration files.

### Changed

- Updated the frontend task detail view with responsive task facts and progress display.
- Improved SportsDynamics pagination validation.
- Improved game cleanup and reprocessing before match updates.
- Improved RGD event parsing and persistence, including setpieces, free kicks, and takers.
- Refreshed the frontend structure and production Docker build.
- Consolidated the current backend orchestration and provider workflow.
- Removed obsolete export, archive, and standalone maintenance script mechanisms.
- Simplified the frontend by removing unused components, imports, and host-specific API configuration.
- Rebuilt and validated the production Docker stack with the shared `scomp` Compose project.

### Fixed

- Corrected request timestamp formatting for generated export filenames.
- Fixed task progress remaining at zero during round processing.
- Fixed task round and identifier visibility in the task detail view.
- Fixed Setpieces fields not being populated from flat RGD payloads.
- Added retry handling for expired signed download URLs.

### Database

- Added cooperative task cancellation support.
- Merged the five existing Alembic heads into a single head: `20260921_003000`.

[1.4.0]: https://github.com/AdrienMahy/Scomp/releases/tag/v1.4.0
[1.3.0]: https://github.com/AdrienMahy/Scomp/releases/tag/v1.3.0
[1.2.0]: https://github.com/AdrienMahy/Scomp/releases/tag/v1.2.0
[1.1.2]: https://github.com/AdrienMahy/Scomp/releases/tag/v1.1.2
[1.1.0]: https://github.com/AdrienMahy/Scomp/releases/tag/v1.1.0
[1.0.0]: https://github.com/AdrienMahy/Scomp/releases/tag/v1.0.0
