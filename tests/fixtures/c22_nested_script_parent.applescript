on makeAdder(k)
	script Adder
		on addTo(v)
			return v + k
		end addTo
	end script
	return Adder
end makeAdder
set a to makeAdder(10)
return a's addTo(5)

