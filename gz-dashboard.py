#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
 Collects statistics on the currently maintained gz releases and publishes to gz-dashboard.json.
"""
import git
import os
import yaml
import requests
import json
import time
import datetime

def find_newest_tag(lst, q):
    valid={'0','1','2','3','4','5','6','7','8','9','.'}
    clean = [s.replace(q, '') for s in lst if (q in s and valid.issuperset(s.replace(q, '')))]
    v0=v1=v2=0
    for i in clean:
        vs=i.split(".")
        if int(vs[0]) > v0:
            v0 = int(vs[0])
            v1 = int(vs[1])
            v2 = int(vs[2])
        elif (int(vs[0]) == v0) and (int(vs[1]) > v1):
            v1 = int(vs[1])
            v2 = int(vs[2])
        elif (int(vs[0]) == v0) and (int(vs[1]) == v1) and (int(vs[2]) >= v2):
            v2 = int(vs[2])
            
    highest_v = q+str(v0)+'.'+str(v1)+'.'+str(v2)
        
    return highest_v


def commit_number_changes():
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


def is_git_repo(path):
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False

repos_path = os.path.dirname(os.path.abspath(__file__)) + '/temp-repos'

if not os.path.exists(repos_path):
    os.makedirs(repos_path, mode = 0o777, exist_ok = False)


gz_release_checks = ["citadel", "fortress", "garden"]

gz_dashboard_dict = {}

for gz_release in gz_release_checks:
    url = 'https://raw.githubusercontent.com/gazebo-tooling/gazebodistro/master/collection-' + gz_release + '.yaml'
    req_url = requests.get(url)
    gz_distro = yaml.safe_load(req_url.content)
    reps = gz_distro['repositories']
    gz_dashboard_dict.update({gz_release:{}})
    for rep in reps:
        repo_path = '{:s}/{:s}'.format(repos_path, rep)
        if not os.path.exists(repo_path):
            repo = git.Repo.clone_from(url=reps[rep]['url'], to_path=repo_path)
        elif not is_git_repo(repo_path):
            repo = git.Repo.clone_from(url=reps[rep]['url'], to_path=repo_path)
        else:
            repo = git.Repo(repo_path)

        list_tags = list([ str(tag).replace('<git.TagReference "refs/tags/',
            '').replace('">','') for tag in repo.tags ])

        
        tag_id_prefix = reps[rep]['version'].replace("ign-", 
            "ignition-").replace("plugin1", "plugin").replace("tools1", 
            "tools").replace("sdf", "sdformat")+'_'

        newest_tag = find_newest_tag(list_tags, tag_id_prefix)

        repo.git.checkout(reps[rep]['version'])

        days_between_tag_to_newest_commit = round((repo.commit("HEAD").committed_date-repo.tags[newest_tag].commit.committed_date)/86400)
        
        days_since_last_tag = round((time.time()-repo.tags[newest_tag].commit.committed_date)/86400)
        
        number_commits_since_tag = int(repo.git.rev_list('--count', repo.commit("HEAD"))) - int(repo.git.rev_list('--count', repo.tags[newest_tag].commit))
        diff_text=repo.git.diff(repo.tags[newest_tag].commit, repo.commit("HEAD"),'--shortstat')
        diff_text_clean=diff_text.replace('deletions(-)','').replace('deletion(-)','').replace('insertions(+)',
                            '').replace('insertion(+)','').replace('files changed','').replace(' ','').split(',')
        if len(diff_text_clean) == 2:
            commited_number_changes_since_tag = int(diff_text_clean[1])
        elif len(diff_text_clean) == 3:    
            code_changes_since_tag = int(diff_text_clean[1])+int(diff_text_clean[2])
        else:
            code_changes_since_tag = 0
            
        
        entry={ rep:{ "newest_tag": {
                        "name": newest_tag,
                        "hash": repo.tags[newest_tag].commit.hexsha,
                        "date": repo.tags[newest_tag].commit.committed_datetime.strftime("%Y-%m-%d %H:%M")},
                     "newest_commit": {
                        "branch": reps[rep]['version'],
                        "hash": repo.commit("HEAD").hexsha,
                        "date": repo.commit("HEAD").committed_datetime.strftime("%Y-%m-%d %H:%M")},
                     "stats": {
                         "days_since_last_tag": days_since_last_tag,
                         "days_between_tag_to_newest_commit": days_between_tag_to_newest_commit,
                         "number_commits_since_tag": number_commits_since_tag,
                         "code_changes_since_tag": code_changes_since_tag}
                     }
                }

        
        gz_dashboard_dict[gz_release].update(entry)


json_object = json.dumps(gz_dashboard_dict, indent=4)

json_path = os.path.dirname(os.path.abspath(__file__)) + "/gz-dashboard.json"

with open(json_path, "w") as outfile:
    outfile.write(json_object)
