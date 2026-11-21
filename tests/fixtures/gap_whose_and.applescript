-- test: no-run
-- test: xfail whose clauses joined with and/or
tell application "Finder"
get name of every disk whose name is not "" and capacity > 0
end tell
