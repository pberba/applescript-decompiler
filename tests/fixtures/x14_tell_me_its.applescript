set x to {1}
tell x
	set y to count
end tell
tell me to set z to 2
using terms from application "Finder"
	set k to 1
end using terms from
with timeout of 5 seconds
	set j to 1
end timeout
return its z

