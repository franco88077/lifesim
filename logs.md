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
