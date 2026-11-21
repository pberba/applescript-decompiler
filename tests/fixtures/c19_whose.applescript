tell application "Finder"
	set f to name of every disk whose name is not ""
end tell
return f

