def custom_sort(branch_name):
    if branch_name == 'develop':
        return 0
    elif branch_name == 'staging':
        return 1
    elif branch_name == 'main':
        return 2
    else:
        return 3

def filter_and_sort_projects(grouped_projects, search_query, min_feature_branches, max_open_mrs, main_sync_status, sort_by, sort_order, projects_data, default_branches):
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

    # Apply sorting
    sorted_projects = sorted(filtered_projects.items(), key=lambda item: item[1]['short_name'].lower())
    if sort_order == 'desc':
        sorted_projects.reverse()

    all_branches = sorted(list(set(branch for p_data in projects_data for branch in p_data.get('branches') or default_branches)), key=custom_sort)
    return dict(sorted_projects), all_branches
