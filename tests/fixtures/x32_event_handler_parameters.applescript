on run argv
	set n to count of argv
	return "got " & n & " argument(s)"
end run
on open theFiles
	repeat with f in theFiles
		log (f as text)
	end repeat
end open

