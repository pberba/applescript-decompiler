set evens to {}
repeat with i from 1 to 6
	if i mod 2 = 0 then
		set end of evens to i
	end if
end repeat
return evens

