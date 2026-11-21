try
	error "boom" number 42
on error errMsg number errNum
	return errMsg & ":" & errNum
end try

