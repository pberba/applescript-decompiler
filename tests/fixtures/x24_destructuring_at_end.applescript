-- `set {a, b} to ...` as the last statement of a handler or branch
-- (no StoreResult follows it).
on pick(flag)
	if flag then
		set {p, q} to {1, 2}
	else
		set {p, q} to {3, 4}
	end if
	try
		set {r, s} to {p, q}
	on error
		set {r, s} to {0, 0}
	end try
	set {u, v} to {r + s, r - s}
end pick
log pick(true)

