-- test: xfail `local` declarations are not emitted
on run
	local a
	set a to 1
	my foo(a)
	return
end run
on foo(q)
	global zz
	set zz to q
	return
end foo

