-- test: xfail `character id N` (key form) is printed as `kfrmID`
-- Algorithms: recursive quicksort checked against NSArray sorting,
-- memoised Fibonacci in a script object, closures built in handlers,
-- labeled parameters, references/copy semantics and text processing.
use AppleScript version "2.4"
use framework "Foundation"
use scripting additions

property seedList : {31, 4, 15, 9, 26, 5, 35, 8, 97, 93, 23, 84, 62, 64, 33, 83}
global callCount

script Memo
	property cache : {}
	on fib(n)
		set callCount to callCount + 1
		if n < 2 then return n
		repeat with entry in cache
			if item 1 of entry = n then return item 2 of entry
		end repeat
		set v to (my fib(n - 1)) + (my fib(n - 2))
		set end of cache to {n, v}
		return v
	end fib
end script

on quicksort(xs)
	if (count of xs) ≤ 1 then return xs
	set pivot to item 1 of xs
	set lesser to {}
	set greater to {}
	repeat with x in rest of xs
		if contents of x < pivot then
			set end of lesser to contents of x
		else
			set end of greater to contents of x
		end if
	end repeat
	return quicksort(lesser) & {pivot} & quicksort(greater)
end quicksort

on makeCounter(startAt, stepBy)
	script Counter
		property current : startAt
		on next()
			set current to current + stepBy
			return current
		end next
	end script
	return Counter
end makeCounter

on clamp given value:v, low:lo, high:hi
	if v < lo then
		return lo
	else if v > hi then
		return hi
	end if
	return v
end clamp

on histogram(xs, bucketSize)
	set buckets to {0, 0, 0, 0, 0, 0, 0, 0, 0, 0}
	repeat with x in xs
		set b to (clamp given value:((contents of x) div bucketSize) + 1, low:1, high:10)
		set item b of buckets to (item b of buckets) + 1
	end repeat
	return buckets
end histogram

on caesar(s, shift)
	set out to ""
	considering case
		repeat with ch in characters of s
			set c to id of ch
			if c ≥ 97 and c ≤ 122 then
				set out to out & (character id (((c - 97 + shift) mod 26) + 97))
			else if c ≥ 65 and c ≤ 90 then
				set out to out & (character id (((c - 65 + shift) mod 26) + 65))
			else
				set out to out & ch
			end if
		end repeat
	end considering
	return out
end caesar

on run
	set callCount to 0
	set sortedMine to quicksort(seedList)
	set sortedObjC to ((current application's NSArray's arrayWithArray:seedList)'s sortedArrayUsingSelector:"compare:") as list
	set sortOk to sortedMine = sortedObjC
	
	set fibs to {}
	repeat with i from 0 to 20 by 5
		set end of fibs to Memo's fib(i)
	end repeat
	
	set c1 to makeCounter(10, 5)
	set c2 to makeCounter(0, -1)
	repeat 3 times
		c1's next()
		tell c2 to next()
	end repeat
	
	-- references and copy semantics
	set original to {1, 2, 3}
	set alias1 to original
	copy original to cloned
	set end of alias1 to 4
	set r to a reference to item 2 of original
	set contents of r to 20
	
	set tally to 0
	set n to 0
	repeat until n ≥ 50
		set n to n + 7
		if n mod 2 = 0 then
			set tally to tally + n
		else if n mod 5 = 0 then
			exit repeat
		end if
	end repeat
	
	with timeout of 10 seconds
		set coded to caesar("Hello, World", 3)
	end timeout
	ignoring case
		set sameWord to ("APPLE" = "apple")
	end ignoring
	return {sortOk, items 1 thru 4 of sortedMine, middle item of sortedMine, last item of sortedMine, fibs, callCount, c1's current, c2's current, original, cloned, tally, n, coded, caesar(coded, 23), sameWord, histogram(seedList, 10)}
end run

