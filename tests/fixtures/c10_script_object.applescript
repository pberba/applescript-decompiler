script Counter
	property tally : 0
	on increment()
		set tally to tally + 1
		return tally
	end increment
end script
tell Counter to increment()
return Counter's increment()

