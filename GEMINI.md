# Project Overview: GitLab Project Status Dashboard

This project is a Flask-based web application designed to provide a centralized dashboard for monitoring the status of multiple GitLab projects. It helps track key development metrics at a glance.

## Core Technologies

- **Backend**: Python with the Flask framework.
- **Frontend**: HTML, Bootstrap 5, and vanilla JavaScript. The UI is inspired by GitLab's "Pajamas" design system.
- **GitLab Integration**: Uses the `python-gitlab` library to communicate with the GitLab API.
- **Data Storage**: A simple JSON file (`projects.json`) managed by `db_manager.py` is used to store the list of projects to be monitored.
- **Caching**: Implements a `FileSystemCache` via `flask-caching` to minimize redundant GitLab API calls and improve performance. The cache is stored in the `cache/` directory.

## Key Features

- **Project Dashboard**: The main view lists all tracked projects in a table.
- **Status Metrics**: For each project, the dashboard displays:
    - Number of open merge requests.
    - Count of feature branches and total branches.
    - Sync status between `main` and `develop` branches.
    - Pipeline and commit status for key branches (e.g., `develop`, `staging`, `main`).
- **Filtering and Sorting**: Users can search for projects and filter them based on criteria like the number of branches or merge requests.
- **Project Management**: Users can add new projects to monitor or remove existing ones directly from the UI.
- **Cache Management**: Provides options to clear the cache for individual or multiple projects to force a data refresh.
- **Logging**: Detailed logging of GitLab API calls and cache events is available when the application is run in debug mode.

## Project Structure

- `app.py`: The main Flask application file. It handles routing, request handling, and orchestrates calls to other modules.
- `gitlab_service.py`: A dedicated module to handle all interactions with the GitLab API. It contains the logic for fetching project data, branches, merge requests, etc.
- `data_processor.py`: Contains the logic for filtering, sorting, and processing the data fetched from GitLab before it's rendered in the template.
- `db_manager.py`: Manages the list of projects to be monitored, reading from and writing to `projects.json`.
- `templates/`: Directory containing the Jinja2 HTML templates (`index.html`, `add_project.html`).
- `assets/`: Contains static files, such as the `icons.svg` sprite sheet.
- `.env`: File for storing environment variables.

## Setup and Configuration

1.  **Dependencies**: Install required Python packages (likely from `pyproject.toml`).
2.  **Environment Variables**: Create a `.env` file in the project root with the following variables:
    - `GITLAB_URL`: The URL of your GitLab instance (e.g., `https://gitlab.com`).
    - `GITLAB_PRIVATE_TOKEN`: Your personal GitLab access token with API scope.
    - `FLASK_DEBUG=1`: (Optional) Set to `1` to enable Flask's debug mode and activate detailed logging.
3.  **Run the Application**: Execute `python app.py` to start the development server.
