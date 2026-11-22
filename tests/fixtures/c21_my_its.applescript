on helper()
	return 7
end helper
on caller()
	return my helper()
end caller
return caller()

