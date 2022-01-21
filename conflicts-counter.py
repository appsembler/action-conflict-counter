#!/usr/local/bin/python
import json
import os
import subprocess


REPO_PATH = '/repo'

PATHS_LIST_SEPARATOR = ','


def check_output(args, cwd=REPO_PATH, **kwargs):
    print('$', ' '.join(args), f'at "{cwd}"')
    output = subprocess.check_output(args, cwd=cwd, **kwargs, stderr=subprocess.STDOUT).decode('utf-8')
    print(output)
    print('\n')
    return output


BOT_SIGNATURE = '<!--- action-conflict-counter --->'


class ConflictReporter:
    """
    Reports count and summary of merge conflicts.
    """

    def __init__(self):
        self.local_base_branch = os.environ['INPUT_LOCAL_BASE_BRANCH']
        self.upstream_repo = os.environ['INPUT_UPSTREAM_REPO']
        self.upstream_branches = os.environ['INPUT_UPSTREAM_BRANCHES']

        current_git_branch = os.environ['GITHUB_REF']
        self.current_git_branch = os.getenv('INPUT_CURRENT_GIT_BRANCH') or current_git_branch

        current_git_repo = f'{os.environ["GITHUB_SERVER_URL"]}/{os.environ["GITHUB_REPOSITORY"]}.git'
        self.current_git_repo = os.getenv('INPUT_CURRENT_GIT_REPO') or current_git_repo

        self.exclude_paths = os.getenv('INPUT_EXCLUDE_PATHS', '').split(PATHS_LIST_SEPARATOR)  # Optional argument

        self.init_git()

    def init_git(self):
        check_output(['git', 'clone', '--quiet', '--no-tags', '--branch', self.local_base_branch,
                      self.current_git_repo, REPO_PATH], cwd='/')

        check_output(['git', 'config', 'user.name', 'GitHub Actions Counter'])
        check_output(['git', 'config', 'user.email', 'dummy@example.com'])
        check_output(['git', 'remote', 'add', 'upstream', self.upstream_repo])

        check_output(['git', 'fetch', '--no-tags', 'origin', f'{self.local_base_branch}:local_base_branch'])
        check_output(['git', 'fetch', '--no-tags', 'origin', f'{self.current_git_branch}:current_git_branch'])

    def report_conflicts(self):
        upstream_branches = self.upstream_branches.split(',')
        adds_conflicts = False

        reports = []
        report_intro = (
            f"Checking git merge conflicts against {self.upstream_repo} \n"
            f"\n"
        )
        reports.append(report_intro)

        for idx, upstream_branch in enumerate(upstream_branches):
            upstream_branch_alias = f'{upstream_branch}_{idx}'
            check_output(['git', 'fetch', '--no-tags', 'upstream',
                          f'{upstream_branch}:{upstream_branch_alias}'])

            base_counter = ConflictCounter('local_base_branch', upstream_branch_alias, self.exclude_paths)
            base_conflicts = base_counter.count_conflicts()
            base_conflicted_files = set(base_counter.conflicting_files())

            current_counter = ConflictCounter('current_git_branch', upstream_branch_alias, self.exclude_paths)
            current_conflicts = current_counter.count_conflicts()
            new_conflicted_files = sorted(set(current_counter.conflicting_files()) - base_conflicted_files)
            new_conflicted_files_str = '\n'.join(new_conflicted_files)

            if current_conflicts > base_conflicts:
                adds_conflicts = True
                change_message = f'Adds {current_conflicts - base_conflicts} new conflicts. How can we do better?'
            elif current_conflicts < base_conflicts:
                change_message = f'Resolves {base_conflicts - current_conflicts} existing conflicts. Amazing!'
            else:
                change_message = f'Good work! No added conflicts.'

            report = (
                f"| Comparing with  | `{upstream_branch}` |\n"
                f"| ---  | --- |\n"
                f"| Benchmark conflicts with `{self.local_base_branch}` | {base_conflicts} |\n"
                f"| Current conflicts | {current_conflicts} |\n"
                f"| Summary | {change_message} |\n"
            )

            if new_conflicted_files:
                report += (
                    f"\n"
                    f"<details><summary>New conflicting files with '{upstream_branch}'</summary>\n"
                    f"\n"
                    f"```\n{new_conflicted_files_str}\n```\n"
                    f"</details>"
                )

            reports.append(report)
            reports.append(BOT_SIGNATURE)

        output_json = json.dumps({
            'report': '\n\n'.join(reports),
            'adds_conflicts': adds_conflicts,
        })

        print(f'::set-output name=conflicts_report_json::{output_json}')


class ConflictCounter:
    """
    Count conflicts in a git repo.

    TODO: Refactor into more Pythonic form
    This document explains what the git: https://appsembler.atlassian.net/l/c/1fTFXxQ2
    """

    def __init__(self, from_branch, to_branch, exclude_paths):
        self.from_branch = from_branch
        self.to_branch = to_branch
        self.exclude_paths = exclude_paths
        self.merge_successful = False
        self.init_git()

    def init_git(self):
        check_output(['git', 'reset', '--hard', self.from_branch])
        try:
            check_output(['git', 'merge', self.to_branch])
            self.merge_successful = True
        except subprocess.CalledProcessError:
            status = check_output(['git', 'status'])
            if 'fix conflicts and run "git commit"' in status:
                self.merge_successful = False
            else:
                # Something's wrong, we don't know what have happened.
                raise

        if not self.merge_successful:  # No need to run on successful merge.
            if self.exclude_paths:
                print('Started excluding paths:', ','.join(self.exclude_paths))
                for path in self.exclude_paths:
                    try:
                        check_output(['git', 'checkout', self.from_branch, '--', path])
                    except subprocess.CalledProcessError as error:
                        # Continue even if there's an error. Until there's a better way,
                        # that's an acceptable method to avoid counting noisy files.
                        print('Error in ignoring path:', f'"{path}".', 'Error message:', error)
                print('Finished excluding paths.')

    def count_conflicts(self):
        if self.merge_successful:
            return 0
        else:
            count = check_output([
                'bash', '-c', 'grep "^=======$" -- $(git ls-files --unmerged | cut -f2 | sort --unique) | wc -l'
            ])
            count = int(count.strip())
        return count

    def conflicting_files(self):
        if self.merge_successful:
            files = []
        else:
            files = check_output(['bash', '-c', 'git ls-files --unmerged | cut -f2 | sort --unique'])
            files = files.strip().split('\n')
        return files

    def conflict_report(self):
        if self.merge_successful:
            report = ''
        else:
            report = check_output([
                'bash', '-c', 'git --no-pager diff --name-only --diff-filter=U | xargs grep -c "^=======$"'
            ])
        return report


ConflictReporter().report_conflicts()
