set L to {1, 2, 3, 4, 5}
set acc to {}
repeat with i from 1 to 2
	set end of acc to items i thru (i + 2) of L
end repeat
repeat 2 times
	set end of acc to text 1 thru 3 of "hello"
end repeat
return acc

