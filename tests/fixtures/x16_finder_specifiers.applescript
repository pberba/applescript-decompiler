tell application "Finder"
	set a to disk "Macintosh HD"
	set b to item 1 of (every disk whose name is in {"x"})
	set c to window id 5
	set d to item after item 1 of disks
	set e to item before item 2 of disks
	set f to every item of startup disk whose name starts with "A" or name contains "b"
	set g to (count disks)
	set h to exists disk "x"
end tell

