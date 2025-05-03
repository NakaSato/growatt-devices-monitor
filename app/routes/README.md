# Routes Organization

This directory contains all the Flask route blueprints organized by functionality.

## Structure

- `api/` - API-related routes for general functionality
- `data/` - Data access and manipulation routes
- `device/` - Device status monitoring and management routes
- `main/` - Main application routes (UI pages, etc.)
- `prediction/` - ML prediction and diagnostics routes
- `operations/` - Operations and maintenance-related routes

## Usage

Each folder follows the same pattern:

- `routes.py` - Contains the actual route handlers
- `__init__.py` - Exports the blueprint for use in the application

The main `__init__.py` in this directory imports all blueprints and makes them available to the application.

## Adding New Routes

To add new routes:

1. Determine which category your route belongs to
2. Add your route handler to the appropriate `routes.py` file
3. If creating a new category:
   - Create a new folder with `routes.py` and `__init__.py`
   - Update `app/routes/__init__.py` to import and export your new blueprint

## Best Practices

- Keep route handlers small and focused
- Move business logic to service classes
- Use consistent error handling
- Document API endpoints with docstrings
