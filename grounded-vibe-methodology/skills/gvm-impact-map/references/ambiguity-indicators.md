# Ambiguity Indicators (default denylist)
#
# These verbs describe activity, not outcome. A Goal containing one of
# these tokens is rejected by the IM-3 ambiguity scan unless the Goal
# also carries a numeric quantity (matching `\d+%?`) on the same line.
#
# The list is loaded by `_ambiguity_scan.load_denylist`. Tokens are
# case-insensitive; one word per line; lines beginning with `#` are
# comments; blank lines are ignored.
#
# A project may extend or override this list by placing
# `.gvm-impact-map.denylist` (additions) and `.gvm-impact-map.allowlist`
# (subtractions) at the project root. Effective denylist =
# (default ∪ project denylist) − project allowlist.
#
# Aspirational verbs with no measurable outcome
launch
improve
enable
support
deploy
build
create
add
deliver
provide
help
make
boost
optimize
optimise
streamline
modernize
modernise
transform
empower
