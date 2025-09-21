# Lifesim change log

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
