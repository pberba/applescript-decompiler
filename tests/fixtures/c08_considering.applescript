set r to {}
considering case
	set end of r to ("ABC" = "abc")
end considering
ignoring white space
	set end of r to ("a b" = "ab")
end ignoring
return r

