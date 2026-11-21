script Base
	on describe()
		return "base"
	end describe
end script
script Child
	property parent : Base
	on describe()
		return "child+" & (continue describe())
	end describe
end script
return Child's describe()
