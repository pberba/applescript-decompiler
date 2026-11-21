-- test: no-run (talks to another application)
tell application "Finder"
	set n to name of startup disk
end tell
return n

