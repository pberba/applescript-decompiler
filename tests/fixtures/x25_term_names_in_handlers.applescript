-- Handler and parameter names that are AppleScript terms need bars.
on |count|(|name|, |length|)
	return (count of |name|) + |length|
end |count|
on describe given label:|text|, size:|number|
	return |text| & ": " & |number|
end describe
log |count|("abc", 2)
log (describe given label:"total", size:5)

