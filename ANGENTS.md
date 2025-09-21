# Lifesim — Agents

## Instructions for Agents

- The title for all pages should begin with **Lifesim —** followed by what the page represents.
  - Examples: **Lifesim — Home**, **Lifesim — Banking**.
  - Use a true em dash (**—**) with a space on either side, not a hyphen (**-**).

- The AI should always consider **modularization** to keep the code clean, organized, easy to understand, and easy to find.

- **Templates** should always have their own directory (e.g., *banking*, *real estate*, *store*, *work*).
  - Each template directory must have its own **style sheet**.
  - Include **special styles** for that section of the website, since all templates will look different from each other.
  - Within each template directory, include a **static** folder that contains:
    - A **styles** directory.
    - A **JavaScript** directory.
    - An **images/media** directory for logos, graphics, or other visual elements.
    - Any other folders required for modularization.

- **Styling guidelines**:
  - Never use drop shadows.
  - Websites should be **dynamic and flexible**, ensuring they look good on all screen sizes.
  - Menus and navigation must **adjust for smaller screens**, such as mobile phones.

- **Commenting guidelines**:
  - Always create **concise but helpful comments** that explain what the code is doing.
  - Remove any **unused comments**.
  - Never leave instructions in comments; comments must be **descriptive, not instructional**.

- **UI hygiene guidelines**:
  - Remove any **unused files** that are not in use.
  - Eliminate **excessive spacing** left behind when removing code.
  - Keep everything **neatly organized** and properly structured.
  - Ensure code is **properly indented** and files remain clean and readable.

- **File upload and security guidelines**:
  - Whenever features include file uploads or allow users to upload media or file types, always check for **security risks**.
  - Ensure users cannot upload **dangerous or harmful files** that may compromise the system.

- **Logging guidelines**:
  - Maintain a **logs.md** file in the main project structure.
  - This file must record:
    - What was changed.
    - How it was implemented.
    - Why it was implemented.
    - Its intended use or purpose.
  - In addition to `logs.md`, implement a **separate logging system** for runtime activity.
    - This system must capture and display **errors, warnings, and issues** to the user.
    - All systems implemented must integrate with this logging system to report:
      - Failed uploads.
      - Non-functioning features or functions.
      - Code that is not working as intended.
    - Ensure logs are clear, accessible, and helpful for troubleshooting.


- **Operational logging system (user-facing)**:
  - Implement a runtime **log system separate from `logs.md`** that surfaces errors and alerts to the user.
  - **Every system/feature must use this logger** (uploads, forms, API calls, background jobs, etc.).
  - The logger must show clear messages when: **uploads fail**, **functions return errors**, **exceptions occur**, or **expected behavior doesn’t happen**.
  - Provide a **user-visible panel/console** and lightweight **inline notifications/toasts** for immediate feedback.
  - Standardize events with: timestamp, component/feature, action, outcome (success/warn/error), and brief description.
  - **No sensitive data** in messages; include IDs/refs only when necessary for troubleshooting.
  - Support **log levels** (info/warn/error) and a **debug mode** that can be toggled for deeper detail.
  - Ensure messages are **accessible and human-readable** (plain language; include remediation steps when possible).
  - Logs must be **separated with breaks** and have clear **headers** for sections or event groups.
  - Logs should be both **easy to read for users** and also include necessary **technical jargon** to help the AI diagnose and fix problems.
  - Logs must support **bug fixing workflows**, providing enough detail for debugging while staying understandable.


- **Log formatting & readability**:
  - Separate log entries with clear **breaks** (e.g., horizontal rules or distinct spacing) and group by **date/session** for quick scanning.
  - Each entry must have a concise **header**: `[LEVEL] Component — Short title` (e.g., `[ERROR] Uploader — File type blocked`).
  - Use a **two-layer message**:
    - **User summary (plain language):** what happened and what the user can do next.
    - **Technical details (jargon):** error codes, exception names, HTTP status, function/module, and trace snippet for debugging.
  - Include standard fields: **timestamp**, **component/feature**, **action**, **result** (success/warn/error), **correlation/request ID**, and **environment** (dev/stage/prod).
  - Ensure entries are **easy to read** (consistent typography/spacing) and **actionable** (clear remediation steps or support link).
  - Provide **filters** (by level/component) and **search** to help locate issues quickly.
  - Offer a **copy-to-clipboard** option for the technical block to aid bug reports.


- **Database update guidelines**:
  - Always ensure updates do not **corrupt data**.
  - Validate and test before applying any migration or update.
  - Guarantee that all updates are **atomic** (either fully applied or not at all).
  - Preserve all **pre-existing data** and prevent accidental overwrites or deletions.
  - Implement **backups** and rollback mechanisms before making structural or schema changes.
  - Log all database operations in both `logs.md` and the runtime logging system for traceability.


- **Database update & data integrity**:
  - Treat all schema and data changes as **migrations** with versioned scripts (forward + rollback).
  - Use **transactions** for multi-step writes; changes must be **atomic** and **idempotent** where possible.
  - **Preserve existing data**: prefer additive, backward-compatible changes (e.g., new columns with defaults) before destructive ones.
  - Require **full backups** (and verified restores) prior to any migration; keep **point-in-time recovery** enabled where supported.
  - Validate inputs at API and DB layers (**constraints**, **foreign keys**, **unique indexes**, **CHECK** constraints) to prevent corruption.
  - Run migrations in **staging** with production-like data, pass integration tests, and measure runtime/locks before production.
  - Provide **automatic rollback** and **data fix** procedures for failed updates; never leave partial state.
  - Maintain **audit logs** for data changes (who/what/when/before→after) without storing sensitive payloads in clear text.
  - Monitor write paths with the **operational logger**: surface failed writes, constraint violations, long-running queries, and timeouts.
  - For destructive operations (DROP/DELETE), require **explicit confirmation** and create **safety snapshots**.


- **File and testing guidelines**:
  - The AI must **never create binary files** as part of its output.
  - All output should remain in source-controlled, human-readable formats (e.g., `.md`, `.js`, `.html`, `.css`).
  - During testing or experimentation, remove any **temporary or unnecessary test files** after completion.
  - Ensure the project directory stays **clean**, with no leftover artifacts from tests.

