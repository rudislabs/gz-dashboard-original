#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
 Shows statistics on gz releases to the terminal with minimal interface.
 Can specify release to check with --check_release and what to --show (all, warn, crit).
"""
import git
import os
import yaml
import requests
import argparse

parser = argparse.ArgumentParser(description='Gazebo Dashboard.')

parser.add_argument('--show', default= 'all', help='Show ["all", "warn", "warn_and_crit", "crit"]')

parser.add_argument('--check_release', default= 'maintained', help=
                    'Check particular GZ release ["maintained", "citadel", "fortress", "garden", ...]')

args = parser.parse_args()

checkable_releases = [ "acropolis", "blueprint", "dome", "citadel", "edifice", "fortress", "garden" ]

class tcol:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def critical_cost_function(days, commits):

    cost = days*3.34 + commits**2
    
    if cost <= 47.0:
        severity_color = tcol.GREEN
        
    elif cost > 47.0 and cost <= 100.0:
        severity_color = tcol.YELLOW
    
    elif cost > 100.0:
        severity_color = tcol.RED
        
    return severity_color


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

def is_git_repo(path):
    try:
        _ = git.Repo(path).git_dir
        return True
    except git.exc.InvalidGitRepositoryError:
        return False


repos_path = os.path.dirname(os.path.abspath(__file__)) + '/temp-repos'

if not os.path.exists(repos_path):
    os.makedirs(repos_path, mode = 0o777, exist_ok = False)

if args.check_release.lower() == "maintained":

    gz_release_checks = ["citadel", "fortress", "garden"]

elif args.check_release.lower() in checkable_releases:

    gz_release_checks = [ args.check_release ]

else:

    print('ERROR: {:s} is not a valid --check_release option.'.format(args.check_release.lower()))
    print('Valid options: {:s}'.format(checkable_releases))

    gz_release_checks = None


if gz_release_checks is not None:

    for gz_release in gz_release_checks:
        url = 'https://raw.githubusercontent.com/gazebo-tooling/gazebodistro/master/collection-' + gz_release + '.yaml'
        req_url = requests.get(url)
        gz_distro = yaml.safe_load(req_url.content)
        reps = gz_distro['repositories']
        print('\n\n+{0:-^10s}+{0:-^18s}+{0:-^30s}+{0:-^27s}+{0:-^19s}+'.format(''))
        print('|{0:^10s}|{1:^18s}|{2:^30s}|{3:^27s}|{4:^19s}| '.format(gz_release, "REPO", "LATEST TAG", "DAYS SINCE TAG TO COMMIT", "COMMITS SINCE TAG"))
        print('+{0:-^10s}+{0:-^18s}+{0:-^30s}+{0:-^27s}+{0:-^19s}+'.format(''))
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

            
            tag_find = reps[rep]['version'].replace("ign-", 
                "ignition-").replace("plugin1", "plugin").replace("tools1", 
                "tools").replace("sdf", "sdformat")+'_'

            newest_tag = find_newest_tag(list_tags, tag_find)

            repo.git.checkout(reps[rep]['version'])

            days_between_tag_to_newest_commit = round((repo.commit("HEAD").committed_date-repo.tags[newest_tag].commit.committed_date)/86400)

            number_commits_since_tag = int(repo.git.rev_list('--count', repo.commit("HEAD"))) - int(repo.git.rev_list('--count', repo.tags[newest_tag].commit))

            term_color=critical_cost_function(days_between_tag_to_newest_commit, number_commits_since_tag)

            if args.show.upper() == "ALL":

                print('\t   |{0:s}{2:^18s}{1:s}|{0:s}{3:^30s}{1:s}|{0:s}{4:^27.2f}{1:s}|{0:s}{5:^19d}{1:s}|'.format(term_color, tcol.ENDC, reps[rep]['version'], newest_tag, days_between_tag_to_newest_commit, number_commits_since_tag))

            elif args.show.upper() == "WARN" and term_color == tcol.YELLOW:

                print('\t   |{0:s}{2:^18s}{1:s}|{0:s}{3:^30s}{1:s}|{0:s}{4:^27.2f}{1:s}|{0:s}{5:^19d}{1:s}|'.format(term_color, tcol.ENDC, reps[rep]['version'], newest_tag, days_between_tag_to_newest_commit, number_commits_since_tag))

            elif args.show.upper() == "WARN_AND_CRIT" and (term_color == tcol.RED or term_color == tcol.YELLOW):

                print('\t   |{0:s}{2:^18s}{1:s}|{0:s}{3:^30s}{1:s}|{0:s}{4:^27.2f}{1:s}|{0:s}{5:^19d}{1:s}|'.format(term_color, tcol.ENDC, reps[rep]['version'], newest_tag, days_between_tag_to_newest_commit, number_commits_since_tag))
            
            elif args.show.upper() == "CRIT" and term_color == tcol.RED:

                print('\t   |{0:s}{2:^18s}{1:s}|{0:s}{3:^30s}{1:s}|{0:s}{4:^27.2f}{1:s}|{0:s}{5:^19d}{1:s}|'.format(term_color, tcol.ENDC, reps[rep]['version'], newest_tag, days_between_tag_to_newest_commit, number_commits_since_tag))

        print('\t   +{0:-^18s}+{0:-^30s}+{0:-^27s}+{0:-^19s}+'.format(''))
