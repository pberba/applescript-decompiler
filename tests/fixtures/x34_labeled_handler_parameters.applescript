on rangeSum from a thru b
	set total to 0
	repeat with i from a to b
		set total to total + i
	end repeat
	return total
end rangeSum

on joinTwo over x onto y
	return x & y
end joinTwo

on tagged from a given label:l
	return l & a
end tagged

set r1 to rangeSum from 1 thru (2 + 2)
set r2 to joinTwo over "a" onto "b"
set r3 to tagged from "x" given label:"y"
{r1, r2, r3}

