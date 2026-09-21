# Changelog

All notable changes to Scomp are documented in this file.

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

[1.0.0]: https://github.com/AdrienMahy/Scomp/releases/tag/v1.0.0
