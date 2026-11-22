set x to 3
if x = 3 then
	if x > 1 then set x to 2
else
	set x to 4
end if
set y to (x is in {1, 2})
set z to (x comes before 5)
set w to not (x ≠ 2)
set t to "a" is not in "b"
set q to x does not contain 1

