# Lifesim

Lifesim is a modular life-simulation dashboard built with Flask. The application currently includes
foundational systems for banking, real estate, shopping, and job planning, each with its own themed
interface and responsive layout.

## Getting started

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the Flask development server:

   ```bash
   flask --app run:app --debug run
   ```

   The application will automatically create a SQLite database (`lifesim.db`) in the project root.

## Runtime logging

Lifesim uses a structured logging system backed by SQLite. All modules log their key actions and
surface warnings through:

- A collapsible console available on every page.
- Toast-style inline alerts for warnings and errors.
- A dedicated `/logs` console with search, counters, and copy-to-clipboard export.

## Project structure

```
app/
  banking/           # Banking blueprint (templates + static assets)
  real_estate/       # Real estate blueprint
  shop/              # Shop blueprint
  job/               # Job blueprint
  logging/           # Logging blueprint and console
  templates/         # Shared base layout
  static/            # Shared styles and scripts
```

Each module keeps assets in its own `static` directory with `styles`, `js`, and `images` folders to
support future expansion.
