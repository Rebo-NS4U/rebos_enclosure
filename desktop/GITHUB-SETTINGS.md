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
