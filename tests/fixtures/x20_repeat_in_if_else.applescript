on f(L)
	set t to 0
	if class of L is list then
		repeat with x in L
			set t to t + x
		end repeat
	else
		set t to 1
	end if
	return t
end f
return f({1, 2})

