import gitlab
from gitlab.exceptions import GitlabGetError
from dateutil.parser import parse
import pytz
from datetime import datetime
from flask_caching import Cache
import os
import logging

config = {
    "DEBUG": True,
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DEFAULT_TIMEOUT": 600,
    "CACHE_DIR": "cache",
    "CACHE_THRESHOLD": 100
}

cache = Cache(config=config)

def init_gitlab_service(app, gitlab_url, private_token):
    global gl
    gl = gitlab.Gitlab(gitlab_url, private_token=private_token)
    cache.init_app(app)
    if app.debug:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("GitLab service initialized in debug mode.")

def get_project_data(full_project_name, branches_to_process):
    logging.info(f"Attempting to get data for project: {full_project_name}")
    project_entry = cache.get(full_project_name)
    if project_entry is None:
        logging.info(f"Cache miss for project: {full_project_name}. Fetching from GitLab API.")
        try:
            logging.info(f"Fetching project: {full_project_name}")
            project = gl.projects.get(full_project_name)
            logging.info(f"Successfully fetched project: {full_project_name}")

            logging.info(f"Listing branches for project: {full_project_name}")
            all_project_branches = project.branches.list(all=True)
            total_branch_count = len(all_project_branches)
            logging.info(f"Found {total_branch_count} branches for project: {full_project_name}")

            feature_branches = [b for b in all_project_branches if b.name not in ['main', 'develop', 'staging', 'beta']]
            total_feature_branch_count = len(feature_branches)

            logging.info(f"Listing open merge requests for project: {full_project_name}")
            open_merge_requests = project.mergerequests.list(state='opened', all=True)
            open_mr_count = len(open_merge_requests)
            logging.info(f"Found {open_mr_count} open merge requests for project: {full_project_name}")

            main_synced_to_develop = 'N/A'
            try:
                logging.info(f"Fetching develop commit for {full_project_name}")
                develop_commit = project.commits.list(ref_name='develop', get_all=True)[0]
                develop_commit_date = parse(develop_commit.committed_date)

                logging.info(f"Fetching main pipeline for {full_project_name}")
                main_pipeline = project.pipelines.list(ref='main', get_all=True)[0]
                main_pipeline_date = parse(main_pipeline.updated_at)

                if main_pipeline_date >= develop_commit_date:
                    main_synced_to_develop = '✅'
                else:
                    main_synced_to_develop = '❌'
                logging.info(f"Main sync status for {full_project_name}: {main_synced_to_develop}")
            except (IndexError, ValueError) as e:
                logging.warning(f"Could not determine main sync status for {full_project_name}: {e}")
                pass

            project_entry = {
                'short_name': full_project_name.split('/')[-1],
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
                pipeline = None
                try:
                    logging.info(f"Fetching pipeline for branch '{branch}' in {full_project_name}")
                    pipeline = project.pipelines.list(ref=branch, get_all=True)[0]
                    pipeline_date = parse(pipeline.updated_at)
                    logging.info(f"Found pipeline for branch '{branch}' in {full_project_name}")
                except (IndexError, ValueError):
                    logging.warning(f"No pipeline found for branch '{branch}' in {full_project_name}")
                    pass

                try:
                    logging.info(f"Fetching commit for branch '{branch}' in {full_project_name}")
                    commit = project.commits.list(ref_name=branch, get_all=True)[0]
                    commit_date = parse(commit.committed_date)
                    logging.info(f"Found commit for branch '{branch}' in {full_project_name}")
                except (IndexError, ValueError):
                    logging.warning(f"No commit found for branch '{branch}' in {full_project_name}")
                    pass

                pipeline_status = pipeline.status if pipeline else '--'

                if pipeline_date:
                    pipeline_date = pipeline_date.astimezone(pytz.timezone('Europe/Paris'))
                if commit_date:
                    commit_date = commit_date.astimezone(pytz.timezone('Europe/Paris'))

                if pipeline_date and commit_date and pipeline_status == 'success':
                    if pipeline_date >= commit_date:
                        status = '✅'

                project_entry['branches'][branch] = {
                    'status': status,
                    'pipeline_date': pipeline_date.strftime('%Y-%m-%d %H:%M:%S') if pipeline_date else 'No pipeline found',
                    'commit_date': commit_date.strftime('%Y-%m-%d %H:%M:%S') if commit_date else 'No commit found',
                    'pipeline_status': pipeline_status if pipeline_status else 'No pipeline found'
                }
            
            logging.info(f"Setting cache for project: {full_project_name}")
            cache.set(full_project_name, project_entry, timeout=600)

        except GitlabGetError as e:
            if e.response_code == 404:
                logging.warning(f"Project not found on GitLab: {full_project_name}")
                project_entry = {
                    'short_name': full_project_name.split('/')[-1],
                    'status': 'Project Not Found',
                    'total_feature_branch_count': 'N/A',
                    'total_branch_count': 'N/A',
                    'open_mr_count': 'N/A',
                    'main_synced_to_develop': 'N/A',
                    'branches': {}
                }
            else:
                logging.error(f"An unexpected GitLab API error occurred for {full_project_name}: {e}")
                raise
    else:
        logging.info(f"Cache hit for project: {full_project_name}")
    return project_entry

def clear_project_cache(project_name):
    cache.delete(project_name)


def get_default_branches():
    return os.environ.get('DEFAULT_BRANCHES', 'develop,staging,main').split(',')
