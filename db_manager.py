import sqlite3
import json
import os
import gitlab_service

DATABASE_FILE = '.projects.db'
JSON_FILE = 'projects.json'

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            name TEXT PRIMARY KEY,
            branches TEXT
        )
    ''')
    conn.commit()
    conn.close()

def migrate_from_json():
    if not os.path.exists(JSON_FILE):
        print(f"Warning: {JSON_FILE} not found. Skipping migration.")
        return

    init_db() # Ensure DB is initialized before migration
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    with open(JSON_FILE, 'r') as f:
        projects_data = json.load(f)

    for project in projects_data:
        name = project['name']
        branches = json.dumps(project.get('branches', [])) # Store branches as JSON string
        cursor.execute('INSERT OR REPLACE INTO projects (name, branches) VALUES (?, ?)', (name, branches))

    conn.commit()
    conn.close()
    print(f"Migration from {JSON_FILE} to {DATABASE_FILE} complete.")

def get_all_projects():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT name, branches FROM projects')
    rows = cursor.fetchall()
    conn.close()

    default_branches = gitlab_service.get_default_branches()

    projects_data = []
    for row in rows:
        name, branches_json = row
        branches = json.loads(branches_json)
        projects_data.append({
            'name': name,
            'branches': branches if branches else default_branches
        })

    return projects_data

def add_project(name, branches=None):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    if branches is None:
        branches = []
    branches_json = json.dumps(branches)
    cursor.execute('INSERT OR REPLACE INTO projects (name, branches) VALUES (?, ?)', (name, branches_json))
    conn.commit()
    conn.close()

def delete_project(name):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM projects WHERE name = ?', (name,))
    conn.commit()
    conn.close()