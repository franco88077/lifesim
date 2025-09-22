# Lifesim change log
## 2025-10-02
- **What**: Added interactive banking insight charts with timeframe controls for balances and APY earnings.
- **How**: Generated daily, monthly, and yearly series in `build_account_insights`, rendered a new chart panel with Chart.js, styled the selector UI, and wired client-side logic for smooth switching.
- **Why**: Players needed quick, uncluttered access to checking, savings, total cash, and interest trends without paging through transaction lists.
- **Purpose**: Gives users focused visual insight into their money movement and growth so planning transfers or deposits stays fast and informed.
## 2025-10-01
- **What**: Unified the styling of banking insight, account, and settings cards and brought the settings overview inline with other banking pages.
- **How**: Created a reusable `summary-card` pattern with configurable CSS variables, applied it to insights, due summaries, account balances, and closure controls, and swapped the standalone settings intro for the shared banking overview header.
- **Why**: Disparate card treatments and an isolated settings banner looked inconsistent and made it harder to reuse the layout in new contexts.
- **Purpose**: Keeps the banking UI cohesive, simplifies future reuse of highlighted cards, and ensures the settings landing matches the presentation established across the module.
## 2025-09-30
- **What**: Prevented the bulk account closure control from appearing when only one bank account is open.
- **How**: Counted open banking accounts in the routes helper, passed a new template flag, and wrapped the “Close Bank Accounts” card in a conditional.
- **Why**: Closing all accounts charged the full bank-wide fee even when a single account remained, penalising players for non-existent closures.
- **Purpose**: Keeps closure actions aligned with available accounts and avoids surprise fees when only checking or savings is active.
## 2025-09-29
- **What**: Streamlined banking visibility by removing the unused policy ledger and monthly service fee field, hiding
  inaccessible tabs, and gating insights, transfers, and home widgets behind actual account availability.
- **How**: Trimmed the settings template, updated banking routes with helper flags, filtered insight/due payloads, toggled
  navigation links, and wrapped template sections so transactions, balances, transfer forms, and closure tools only appear
  when the user owns the relevant accounts.
- **Why**: Players without checking or savings access saw misleading options and empty data, while the redundant fee input
  duplicated account-specific charges.
- **Purpose**: Keeps the UI focused on actionable controls, clarifies onboarding when no bank accounts exist, and prevents
  misconfiguration by eliminating obsolete settings.
## 2025-09-28
- **What**: Fixed the account opening API to total deposits correctly and added test coverage.
- **How**: Updated the sum operation in `banking/routes.py` to unpack the full selection tuple and
  introduced a pytest verifying `/banking/api/accounts/open` accepts valid payloads and responds
  with the expected JSON.
- **Why**: The previous implementation raised a `ValueError` during tuple unpacking, preventing
  players from opening accounts even with valid deposits.
- **Purpose**: Keeps the onboarding workflow reliable and protects against regressions by
  exercising the happy-path API response in automated tests.
## 2025-09-27
- **What**: Moved the bank account onboarding workflow from the main hub to the banking home page and restored the
  account opening interaction.
- **How**: Reworked the index route, template, styles, and script to drop the modal, extended the banking home route with
  onboarding data, added the modal and call-to-action to the banking template, ported supporting styles and JavaScript,
  and refreshed copy to direct players to the new action.
- **Why**: Opening accounts on the hub was confusing and the button no longer responded, preventing players from creating
  checking or savings accounts.
- **Purpose**: Centralises onboarding where balances live, keeps the hub focused on at-a-glance metrics, and ensures the
  open-account button now launches the modal and calls the API successfully.
## 2025-09-26
- **What**: Introduced an account opening workflow, revamped banking insights, added due summaries, and ensured the bank
  name is consistent across the app.
- **How**: Added a modal on the home page to open checking or savings accounts with configurable deposits, created a
  `/banking/api/accounts/open` endpoint, recalculated account due data, refreshed the insights template with structured
  panels, extended settings with opening deposit requirements, and surfaced the bank name through the base layout context.
- **Why**: Players now begin with only cash and need guidance to create accounts, plus clearer insight cards and due-date
  messaging make it easier to understand obligations and interest earnings.
- **Purpose**: Provides a professional banking experience that mirrors onboarding flows, keeps account requirements
  obvious, and maintains branding cohesion from navigation through detailed reports.
## 2025-09-25
- **What**: Rebuilt banking transfers into a unified source-to-destination flow, added a full ledger view, refreshed account
  insights with anchor date calculations, and tightened the dashboard styling.
- **How**: Introduced a general `/api/transfer/move` endpoint with reusable balance update helpers, created a paginated
  `/banking/transactions` route and template, expanded settings to capture per-account minimums and fees, enhanced interest
  insight logic to project next payouts, and retuned the home/transfer UI plus CSS to emphasise ledger actions without cash
  noise.
- **Why**: Players needed a single transfer form that respects account guardrails, clearer visibility into upcoming charges
  and interest credits, and a way to audit more than four transactions without cash cluttering the history.
- **Purpose**: Keeps cash management intuitive, highlights policy-driven anchor dates, and makes it easier to review and
  configure banking behaviour while maintaining accessible styling.
## 2025-09-24
- **What**: Simplified the banking dashboard language, resized account tiles, and hardened transfer commits.
- **How**: Replaced canned descriptions on the home and transfer templates, tightened typography in the
  banking stylesheet, removed account category labels, and switched the transfer endpoints to commit updates
  directly on the shared SQLAlchemy session.
- **Why**: UI copy overstated instant syncing, the account headers appeared oversized, and deposits/withdrawals
  occasionally failed due to nested transactions.
- **Purpose**: Keeps messaging aligned with actual behavior, presents account names at a comfortable scale,
  and ensures cash movements persist reliably without raising `InvalidRequestError`.

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
