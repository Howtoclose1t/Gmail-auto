# Maintenance Log

## Updates - 2026-06-26 - v2.2.0

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
