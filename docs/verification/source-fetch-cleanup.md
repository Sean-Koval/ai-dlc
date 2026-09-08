# Disposable source cleanup and container verification

PR25 run34168248976 passed all four Linux jobs but failed one Mac Intel profile
resolution test when temporary repository cleanup encountered a nonempty `.git`.
The original Mac timing has not been reproduced on the existing Apple silicon
host. A real Git2.55.0 probe compiled from the official v2.55.0 source tag completed
30 resolutions without that deletion error and recorded detached automatic
maintenance children. This establishes a background writer hazard, not proof
that it caused that particular CI event.

Disposable source fetches now pass `--no-auto-maintenance`, retaining exact ref
validation and all existing cleanup/error handling. They do not change Git global
configuration or introduce retry/delete suppression. The flag is documented by
[Git fetch](https://git-scm.com/docs/git-fetch); Git2.55's
[maintenance configuration](https://github.com/git/git/blob/v2.55.0/Documentation/config/maintenance.adoc)
describes automatic detachment. A real Trace2 regression failed on the existing
maintenance child before the fix and verifies that resolution still returns the
expected commit without starting maintenance after the fix.

The actual Ubuntu24.04 arm64 container at candidate9eaf11a bootstrapped successfully
but its required test run failed the distribution privacy check. The checkout root
also occurred inside ordinary `account/workspace` prose. The scanner now checks
rooted path boundaries and preserves literal private-user detection. Nine focused
cases cover prose, adjacent path names, real descendants, quoted roots and file
URIs. Three false positives failed before the correction. The actual container's
wheel/source-distribution case plus all nine scanner cases then passed (10tests,
5.19seconds). This probe used a dirty copy of the test repair atop9eaf11a and is
not an exact merged-revision or complete-container qualification claim.

This is a repair under #14, not a new public behavior contract; the reviewed
specification judgment is recorded in the child work record. Independent review accepted the five-file repair and independently reran 11
focused cases. The affected source/bundle suite passed 303 tests, and the real
Trace2 case also passed using compiled Git2.55.0. All five required checks passed
on the dirty candidate based on9eaf11a, including 1,418 tests in343.31seconds;
the ignored receipt is `pr25-repair-required.json`. Fresh Mac CI and exact
merged-revision evidence remain pending.
