script S
	on f(a, b)
		return a
	end f
end script
on g(a)
	continue g(a)
end g
on h given foo:x
	continue h given foo:x
end h
on k(z)
	return S's f(1, 2)
end k

