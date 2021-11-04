# Merge Conflict Counter

This action counts any merge conflicts in your repository.


## How to use it?

Reuse the template below by placing it in your repository's workflows e.g. `.github/workflow/conflicts_report.yml`:

```yml
on: [pull_request]
name: 'Merge conflicts'

jobs:
  report:
    name: 'Report'
    uses: appsembler/action-conflict-counter/.github/workflows/report-via-comment.yml@main
    with:
      local_base_branch: 'main'  # Your repositories main/master branch name
      upstream_repo: 'https://github.com/edx/edx-platform.git'  # Upstream repository that you've forked from
      upstream_branch: 'master'  # Upstream repository's main/master branch name
    secrets:
      github_token: ${{ secrets.GITHUB_TOKEN }}
```


# Author

Omar Al-Ithawi at Appsembler.

This action has been modified from 
[**@OliverNybroe**'s `action-conflict-finder`](https://github.com/olivernybroe/action-conflict-finder).
