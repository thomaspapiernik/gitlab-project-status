from flask import Flask, render_template, redirect, url_for, request, send_from_directory, jsonify
import os
from dotenv import load_dotenv

import db_manager
import gitlab_service
import data_processor

load_dotenv()

app = Flask(__name__)
app.debug = os.environ.get('FLASK_DEBUG') == '1'

# Initialize GitLab service with app instance for caching
gitlab_service.init_gitlab_service(app, os.environ.get("GITLAB_URL", "https://gitlab.com"), os.environ.get("GITLAB_PRIVATE_TOKEN"))



@app.route('/')
def index():
    search_query = request.args.get('search_query', '')
    min_feature_branches = request.args.get('min_feature_branches', type=int)
    max_open_mrs = request.args.get('max_open_mrs', type=int)
    main_sync_status = request.args.get('main_sync_status', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    projects_data = db_manager.get_all_projects()

    grouped_projects = {}
    default_branches = gitlab_service.get_default_branches()

    for project_data in projects_data:
        full_project_name = project_data['name']
        branches_to_process = project_data.get('branches', default_branches)
        project_entry = gitlab_service.get_project_data(full_project_name, branches_to_process)
        grouped_projects[full_project_name] = project_entry

    filtered_projects, all_branches = data_processor.filter_and_sort_projects(
        grouped_projects, search_query, min_feature_branches, max_open_mrs, main_sync_status, sort_by, sort_order, projects_data, default_branches
    )

    return render_template('index.html', projects=filtered_projects, all_branches=all_branches, search_query=search_query, min_feature_branches=min_feature_branches, max_open_mrs=max_open_mrs, main_sync_status=main_sync_status, sort_by=sort_by, sort_order=sort_order)

@app.route('/add_project', methods=['GET', 'POST'])
def add_project_route():
    if request.method == 'POST':
        project_name = request.form['project_name']
        branches_str = request.form['branches']
        branches = [b.strip() for b in branches_str.split(',')] if branches_str else []
        db_manager.add_project(project_name, branches)
        gitlab_service.clear_project_cache(project_name) # Clear cache for the new project
        return redirect(url_for('index'))
    return render_template('add_project.html')

@app.route('/clear_cache/<path:project_name>')
def clear_project_cache(project_name):
    gitlab_service.clear_project_cache(project_name)
    return redirect(url_for('index'))

@app.route('/delete_project/<path:project_name>', methods=['POST'])
def delete_project_route(project_name):
    db_manager.delete_project(project_name)
    gitlab_service.clear_project_cache(project_name) # Clear cache for the deleted project
    return redirect(url_for('index'))

@app.route('/clear_selected_cache', methods=['POST'])
def clear_selected_cache():
    selected_projects = request.form.getlist('selected_projects')
    for project_name in selected_projects:
        gitlab_service.clear_project_cache(project_name)
    return redirect(url_for('index'))

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/refresh_projects')
def refresh_projects():
    search_query = request.args.get('search_query', '')
    min_feature_branches = request.args.get('min_feature_branches', type=int)
    max_open_mrs = request.args.get('max_open_mrs', type=int)
    main_sync_status = request.args.get('main_sync_status', '')
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')

    projects_from_db = db_manager.get_all_projects()
    groups_from_db = db_manager.get_all_groups()

    all_project_names = {p['name'] for p in projects_from_db}
    for group_id in groups_from_db:
        projects_in_group = gitlab_service.get_projects_from_group(group_id)
        for project_name in projects_in_group:
            all_project_names.add(project_name)

    projects_data = []
    for project_name in all_project_names:
        # Find original project data to get branches, if it exists
        original_project = next((p for p in projects_from_db if p['name'] == project_name), None)
        branches = original_project['branches'] if original_project else gitlab_service.get_default_branches()
        projects_data.append({'name': project_name, 'branches': branches})

    grouped_projects = {}
    default_branches = gitlab_service.get_default_branches()

    for project_data in projects_data:
        full_project_name = project_data['name']
        branches_to_process = project_data.get('branches', default_branches)
        project_entry = gitlab_service.get_project_data(full_project_name, branches_to_process)
        grouped_projects[full_project_name] = project_entry

    filtered_projects, all_branches = data_processor.filter_and_sort_projects(
        grouped_projects, search_query, min_feature_branches, max_open_mrs, main_sync_status, sort_by, sort_order, projects_data, default_branches
    )

    return jsonify(projects=filtered_projects, all_branches=all_branches)

if __name__ == '__main__':
    app.run(port=8000)
