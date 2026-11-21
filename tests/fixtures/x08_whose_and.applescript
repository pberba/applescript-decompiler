tell application "Finder"
	get name of every disk whose name is not "" and capacity > 0
end tell

