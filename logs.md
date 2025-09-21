# Lifesim change log

## 2025-09-23
- **What**: Refined the banking transaction ledger with inline dividers and scaled down the account cards
  for cash, checking, and savings.
- **How**: Adjusted the banking stylesheet to remove card backgrounds from transactions, add subtle list
  separators, and tighten typography plus spacing on the account summaries.
- **Why**: The banking dashboard needed a cleaner, corporate look with clearer separation between ledger
  entries and less overpowering account headings.
- **Purpose**: Provides a minimalist presentation that keeps focus on the transaction data while ensuring
  account labels feel balanced within the dashboard layout.

## 2025-09-22
- **What**: Rebuilt the banking home into a two-column Account Activity view, introduced a dedicated insights
  page, refreshed the transfer center, and renamed Money on Hand to Cash across the banking module.
- **How**: Updated the banking blueprint to serve recent transactions, added an insights route and template,
  revised the home and transfer templates with new layouts, adjusted styles and scripts for the redesigned
  experience, and seeded existing accounts with the new Cash naming.
- **Why**: The banking area needed clearer separation between balance monitoring, policy guidance, and transfer
  workflows while aligning terminology with the updated product language.
- **Purpose**: Gives players an at-a-glance look at activity, moves insights off the home page, simplifies
  transfers, and keeps terminology consistent throughout the banking system.

## 2025-09-21
- **What**: Updated the logging blueprint to expose its static assets and verified the logs console
  loads correctly.
- **How**: Added the `static_folder="static"` argument when constructing the logging blueprint and
  reloaded the Flask dev server to hit `/logs/` plus the stylesheet and script endpoints.
- **Why**: Without the static folder registered, the console page raised `BuildError` exceptions
  when resolving `/logs/static/...` assets, breaking its layout.
- **Purpose**: Restores the dedicated logging console so users can review runtime activity with the
  intended styles and interactivity.

## 2024-04-08
- **What**: Established the foundational Flask application with modular blueprints for the home hub,
  banking, real estate, shop, and job systems. Added a shared base layout, responsive navigation, and
  system-specific templates, styles, and scripts.
- **How**: Built an application factory (`app/__init__.py`) that registers blueprints and initializes
  SQLAlchemy. Created dedicated directories for each module with isolated assets and unique designs.
- **Why**: Provides a maintainable foundation where each system can evolve independently while sharing
  common infrastructure.
- **Purpose**: Serves as the starting point for future LifeSim features and user interactions.

- **What**: Implemented a structured runtime logging service with persistence, log API, and user-facing
  consoles (inline panel, toasts, and dedicated log page).
- **How**: Added a `SystemLog` model, a `LogManager` helper, and the `/logs/feed` endpoint. Wired each
  blueprint to log activity and surfaced warnings in the UI with polling JavaScript.
- **Why**: Ensures transparency for system behavior, aids debugging, and satisfies operational logging
  requirements.
- **Purpose**: Gives players and developers insight into system health and anomalies during gameplay.

## 2024-04-09
- **What**: Expanded the banking dashboard with live cash, checking, and savings balances, interactive
  transfer forms, and a running transaction ledger tied into the runtime logger.
- **How**: Supplied richer context from the banking blueprint, rebuilt the dashboard template with new
  UI components, scripted client-side state management for transfers, and refreshed the banking styles.
- **Why**: Players need a dedicated money-movement workflow that mirrors real banking behavior and
  provides accountability for every action.
- **Purpose**: Delivers the envisioned, more complex banking system that tracks liquidity, supports
  cash-to-account transfers, and records each event for future review.

## 2024-04-10
- **What**: Split the banking experience into a dedicated home page and transfer center, removed the
  deprecated goals section, and introduced preset descriptions for cash movements alongside a fees and
  interest briefing.
- **How**: Added new templates for the banking home and transfer pages, updated the blueprint routes
  and assets to serve the new structure, reworked the JavaScript to rely on automatic transaction
  narratives, and refreshed the banking styles with navigation and insight layouts.
- **Why**: The banking module needed clearer navigation, automated transfer labeling, and explicit
  account policy messaging to match the updated product direction.
- **Purpose**: Gives players a streamlined money hub that highlights balances, surfaces fees before
  they post, and keeps every transfer consistently documented.

## 2024-04-11
- **What**: Migrated the banking system to the database, added a configurable settings console, and
  refreshed the banking UI for a bright theme with a wider container.
- **How**: Introduced SQLAlchemy models for bank settings, accounts, and transactions; built service
  helpers to seed defaults and serialize ledger data; rewrote the banking routes to persist transfers
  and expose JSON endpoints; implemented the settings template and form handlers; modernized the
  banking JavaScript to sync with the API; and redesigned both base and banking styles for a 1200px
  light layout.
- **Why**: Persistent balances, fees, and interest rates are essential for reliable simulation play,
  while administrators need an interface to tune banking behavior without touching code.
- **Purpose**: Ensures every transaction and configuration change is tracked, empowers tuning through
  a dedicated settings page, and presents the banking module in a readable light theme across devices.
