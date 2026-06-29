# Maintenance Log

## Updates - 2026-06-29 - v2.3.1

### Overview

Refined the verification-code notification layout so one-time passwords are easier to read and copy.

### Changed

- Moved the verification code out of the metadata rows into a dedicated bordered card.
- Moved the `Copy code` button into the verification-code card and kept only one copy button in the popup.
- Increased the verification-code popup height so metadata, actions, and summary content have enough space.

## Updates - 2026-06-29 - v2.3.0

### Overview

Improved Gmail Auto v2 push-listener shutdown behavior, notification metadata, reversible mailbox actions, and first-run setup documentation.

### Added

- Added the received date to the desktop notification UI.
- Added Gmail `internalDate` based date formatting with numeric UTC offsets, for example `2026-06-26 14:59:14 (UTC+02:00)`.
- Added undo support for archive actions through `Unarchive`.
- Added undo support for delete actions through `Restore`.
- Added `FUTURE_UPDATES.md` as a place to track future work, including strikethrough examples.

### Changed

- Changed archive and delete buttons to behave like the existing Star/Unstar toggle mechanism.
- Changed push notification shutdown to close Pub/Sub subscriber resources and executor pools more cleanly.
- Changed push processing so Ctrl+C stops after the current in-flight Ollama analysis instead of continuing through the remaining batch.

### Fixed

- Fixed Ctrl+C not ending the push listener cleanly in PowerShell.
- Prevented push state from advancing when shutdown interrupts a notification batch, so unprocessed emails can be retried on the next run.
- Avoided localized Windows timezone names in the notification date display.

## Updates - 2026-06-27 - v2.2.0

### Overview

Improved Gmail Auto v2 local Ollama configuration and prompt maintenance so the English git version keeps model behavior in code instead of scattered startup environment variables.

### Added

- Added the `OLLAMA_KEEP_ALIVE_FOREVER` switch to control whether the Ollama model stays loaded.
- Added `OLLAMA_KEEP_ALIVE` and pass `keep_alive` to Ollama `/api/chat` requests.


### Changed

- Moved the analysis prompt into a dedicated `prompt.py` file.
- Set the default Ollama model in code to `qwen3:4b`, with `qwen3:8b` left as the documented larger-model option.


### Fixed

- Avoided Ollama `400 Bad Request` failures by sending indefinite `keep_alive` as integer `-1` instead of string `"-1"`.

## Updates - 2026-06-26 - v2.1.0

### Overview

Optimized the Gmail Auto v2 desktop popup so common email actions feel closer to Gmail behavior and reduce inconsistent states after user actions.

### Added

- Added a quick reply feature.
- Added a delete button.
- Added support for starring emails.
- Added Gmail / Material style icons.

### Changed

- Combined the Star and Unstar actions into a single toggle button.
- Archived emails can no longer be starred or unstarred.
- Changed archive behavior so the notification window no longer closes automatically.
- Updated README.
- Improved and refined the application icons.

### Fixed

- Fixed inconsistent button states after archive, delete, and star actions.
