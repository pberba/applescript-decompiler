-- Integers outside 16 bits are stored as long integers, not Fixnums.
on limits()
	set small to 32767
	set big to 40000
	set negative to -40000
	set huge to 536870911
	return {small, big, negative, huge, big * 3}
end limits
log limits()

