# GitHub update status

Settings → GitHub checks the official Enclosure repository's default branch when
opened. **Check for updates** refreshes the result; **Open GitHub** opens the
repository. Installed and remote commit IDs and the last check time appear below
the status. This check does not install updates or change Git refs.

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
