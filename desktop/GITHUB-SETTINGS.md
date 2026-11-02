# GitHub update status

Settings → GitHub checks the official Enclosure repository's default branch when
opened. **Check for updates** refreshes the result; **Open GitHub** opens the
repository. The panel includes:

- A colored sync status with an explanation and ahead/behind commit counts.
- Installation type, local branch and GitHub default branch.
- Full installed and remote commit IDs, titles, authors, dates and commit links.
- A comparison link when the installed and GitHub revisions differ.
- A count of changed or untracked entries, with up to 12 paths and change types.
- Up to five recent incoming commits when GitHub reports a different revision.
- The date and time of the last completed check.

Local changes describe the whole linked checkout; untracked directories count as
one entry. For copied installations, the change flag reflects deployment time.

This check does not install updates or change Git refs.

Linked installations read their checkout's revision and report local changes.
Copied installations record the source revision during deployment. Older copied
installations without a recorded revision show an unknown-version message until
redeployed from a Git checkout. GitHub connection failures appear as errors,
never as an up-to-date result. Unpublished local commits use locally available
Git history for comparison when GitHub cannot compare them.

The checker uses the public GitHub API without credentials. API rate limits or
network failures can prevent a check; retry with the refresh button.

Verification: run `python3 -m unittest discover -s desktop/tests -p test_github_status.py`,
plus `test_deploy.py` and `test_update.py` for deployment and updater coverage.

## Projects and controls

The project selector discovers GitHub checkouts directly under `~/code`, includes
linked Enclosure sources, and remembers folders added with **Add local project**.
Only folders whose `origin` is a GitHub repository can be managed. Saved project
paths stay in the user's XDG state directory and are never shipped in the payload.
**Browse my GitHub projects** lists up to 100 repositories owned by the current
GitHub CLI account. Enter any accessible `owner/repository` directly to access
collaborator projects. **Clone project** requires a new destination folder.
Private repositories use the existing `gh` login; **GitHub login in terminal**
opens the normal GitHub CLI web login. Credentials are handled by `gh`.

For the selected local checkout:

- Fetch origin, pull the current branch with `--ff-only`, or push the current
  branch to origin. Push also sets its upstream and never force-pushes.
- Select an existing local branch, or create and switch to a new branch. Pull
  and branch changes require a clean worktree.
- Filter and select individual files, review their diff, stage or unstage them,
  and commit only
  selected staged files. Unrelated staged work stays in place. Both paths of a
  rename must be selected for its commit. New unstaged edits require restaging.
- Create a draft or ready pull request with a title, description and base branch.
  The branch must already be pushed. The panel never silently pushes for a PR.
- Open the selected folder, terminal, issues, pull requests or commit pages.
- Review the eight most recent local commits, even when GitHub is unavailable.

Commit, push and pull request buttons show a review dialog with the destination
and operation details before execution. Action output and failures appear in the
panel. Fetch/pull/push use the selected checkout's origin. A different push URL is
rejected, and file selections are validated against current repository state.
Switching or pulling linked desktop sources can hot-reload the shell; no service
restart is performed by this panel.

The GitHub CLI is included in the desktop runtime packages. Without it, public
status checks and HTTPS clones still work; account browsing and PR creation need
`gh`. Tests in `desktop/tests/test_github_projects.py` use temporary repositories
for write operations, with mocked GitHub publishing.
