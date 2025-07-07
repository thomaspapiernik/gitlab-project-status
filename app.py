from flask import Flask, render_template, redirect, url_for, request
from flask_caching import Cache
import json
import gitlab
import os
from dotenv import load_dotenv
from dateutil.parser import parse
import pytz
from datetime import datetime
from gitlab.exceptions import GitlabGetError

load_dotenv()

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'FileSystemCache', 'CACHE_DIR': 'cache', 'CACHE_THRESHOLD': 30, 'CACHE_DEFAULT_TIMEOUT': 600})

private_token = os.environ.get("GITLAB_PRIVATE_TOKEN")
gitlab_url = os.environ.get("GITLAB_URL", "https://gitlab.com")

gl = gitlab.Gitlab(gitlab_url, private_token=private_token)

def custom_sort(branch_name):
    if branch_name == 'develop':
        return 0
    elif branch_name == 'staging':
        return 1
    elif branch_name == 'main':
        return 2
    else:
        return 3

@app.route('/')
def index():
    search_query = request.args.get('search_query', '')
    min_feature_branches = request.args.get('min_feature_branches', type=int)
    max_open_mrs = request.args.get('max_open_mrs', type=int)
    main_sync_status = request.args.get('main_sync_status', '')
    with open('projects.json') as f:
        projects_data = json.load(f)

    grouped_projects = {}
    default_branches = ["develop", "staging", "main"]
    for project_data in projects_data:
        full_project_name = project_data['name']
        short_project_name = full_project_name.split('/')[-1]

        branches_to_process = project_data.get('branches', default_branches)

        try:
            project_entry = cache.get(full_project_name)
            if project_entry is None:
                project = gl.projects.get(full_project_name)
                all_project_branches = project.branches.list(all=True)
                total_branch_count = len(all_project_branches)
                feature_branches = [b for b in all_project_branches if b.name not in ['main', 'develop', 'staging', 'beta']]
                total_feature_branch_count = len(feature_branches)
                open_merge_requests = project.mergerequests.list(state='opened', all=True)
                open_mr_count = len(open_merge_requests)

                main_synced_to_develop = 'N/A'
                try:
                    develop_commit = project.commits.list(ref_name='develop', get_all=True)[0]
                    develop_commit_date = parse(develop_commit.committed_date)
                    main_pipeline = project.pipelines.list(ref='main', get_all=True)[0]
                    main_pipeline_date = parse(main_pipeline.updated_at)

                    if main_pipeline_date >= develop_commit_date:
                        main_synced_to_develop = '✅'
                    else:
                        main_synced_to_develop = '❌'
                except (IndexError, ValueError):
                    pass

                project_entry = {
                    'short_name': short_project_name,
                    'total_feature_branch_count': total_feature_branch_count,
                    'total_branch_count': total_branch_count,
                    'open_mr_count': open_mr_count,
                    'main_synced_to_develop': main_synced_to_develop,
                    'project_web_url': project.web_url,
                    'branches': {}
                }

                for branch in branches_to_process:
                    pipeline_date = None
                    commit_date = None
                    status = '❌'
                    try:
                        pipeline = project.pipelines.list(ref=branch, get_all=True)[0]
                        pipeline_date = parse(pipeline.updated_at)
                    except (IndexError, ValueError):
                        pass

                    try:
                        commit = project.commits.list(ref_name=branch, get_all=True)[0]
                        commit_date = parse(commit.committed_date)
                    except (IndexError, ValueError):
                        pass

                    if pipeline_date:
                        pipeline_date = pipeline_date.astimezone(pytz.timezone('Europe/Paris'))
                    if commit_date:
                        commit_date = commit_date.astimezone(pytz.timezone('Europe/Paris'))

                    if pipeline_date and commit_date:
                        if pipeline_date >= commit_date:
                            status = '✅'

                    project_entry['branches'][branch] = {
                        'status': status,
                        'pipeline_date': pipeline_date.strftime('%Y-%m-%d %H:%M:%S') if pipeline_date else 'No pipeline found',
                        'commit_date': commit_date.strftime('%Y-%m-%d %H:%M:%S') if commit_date else 'No commit found'
                    }
                cache.set(full_project_name, project_entry, timeout=600)
            grouped_projects[full_project_name] = project_entry

        except GitlabGetError as e:
            if e.response_code == 404:
                grouped_projects[full_project_name] = {
                    'short_name': short_project_name,
                    'status': 'Project Not Found',
                    'total_feature_branch_count': 'N/A',
                    'total_branch_count': 'N/A',
                    'open_mr_count': 'N/A',
                    'main_synced_to_develop': 'N/A',
                    'branches': {}
                }
            else:
                # Re-raise other GitlabGetErrors
                raise
    all_branches = sorted(list(set(branch for p_data in projects_data for branch in p_data.get('branches', default_branches))), key=custom_sort)

    filtered_projects = {}
    for project_name, project_data in grouped_projects.items():
        # Apply search query filter
        if search_query and search_query.lower() not in project_name.lower() and search_query.lower() not in project_data['short_name'].lower():
            continue

        # Apply min_feature_branches filter
        if min_feature_branches is not None and project_data['total_feature_branch_count'] != 'N/A' and project_data['total_feature_branch_count'] < min_feature_branches:
            continue

        # Apply max_open_mrs filter
        if max_open_mrs is not None and project_data['open_mr_count'] != 'N/A' and project_data['open_mr_count'] > max_open_mrs:
            continue

        # Apply main_sync_status filter
        if main_sync_status:
            if main_sync_status == 'synced' and project_data['main_synced_to_develop'] != '✅':
                continue
            if main_sync_status == 'not_synced' and project_data['main_synced_to_develop'] != '❌':
                continue

        filtered_projects[project_name] = project_data

    return render_template('index.html', projects=filtered_projects, all_branches=all_branches, search_query=search_query, min_feature_branches=min_feature_branches, max_open_mrs=max_open_mrs, main_sync_status=main_sync_status)

@app.route('/clear_cache/<path:project_name>')
def clear_project_cache(project_name):
    cache.delete(project_name)
    return redirect(url_for('index'))

@app.route('/clear_selected_cache', methods=['POST'])
def clear_selected_cache():
    selected_projects = request.form.getlist('selected_projects')
    for project_name in selected_projects:
        cache.delete(project_name)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)