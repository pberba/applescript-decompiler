-- Task queue: script-object "classes" with inheritance and continue,
-- factories that capture handler parameters, a retry loop with error
-- numbers, an NSMutableArray-backed queue and an NSMutableOrderedSet.
use AppleScript version "2.4"
use framework "Foundation"
use scripting additions

property maxRetries : 3
property statusNames : {pending:"PENDING", ok:"OK", failed:"FAILED"}
global completed, attemptLog

script BaseTask
	property taskName : "base"
	property attempts : 0
	on describe()
		return taskName & "#" & attempts
	end describe
	on perform()
		error "not implemented" number 900
	end perform
	on execute()
		set attempts to attempts + 1
		return perform()
	end execute
end script

on makeTask(theName, failuresBeforeSuccess, payload)
	script CountingTask
		property parent : BaseTask
		property taskName : theName
		property failuresLeft : failuresBeforeSuccess
		on perform()
			if failuresLeft > 0 then
				set failuresLeft to failuresLeft - 1
				error taskName & " transient failure" number 700 + failuresLeft
			end if
			return payload
		end perform
		on describe()
			return "[" & (continue describe()) & "]"
		end describe
	end script
	return CountingTask
end makeTask

on makeSquareTask(n)
	script SquareTask
		property parent : BaseTask
		property taskName : "square" & n
		on perform()
			return n * n
		end perform
	end script
	return SquareTask
end makeSquareTask

on runWithRetry(aTask)
	repeat with tryNumber from 1 to maxRetries
		try
			set theResult to aTask's execute()
			set end of attemptLog to (aTask's describe()) & "=ok"
			return {status:ok of statusNames, value:theResult, tries:tryNumber}
		on error errMsg number errNum
			if errNum ≥ 700 and errNum < 800 then
				set end of attemptLog to (aTask's describe()) & "=retry(" & errNum & ")"
			else
				set end of attemptLog to (aTask's describe()) & "=fatal(" & errNum & ")"
				exit repeat
			end if
		end try
	end repeat
	return {status:failed of statusNames, value:missing value, tries:tryNumber}
end runWithRetry

on joinList(theList, delimiter)
	set arr to current application's NSArray's arrayWithArray:theList
	return (arr's componentsJoinedByString:delimiter) as text
end joinList

on run
	set completed to 0
	set attemptLog to {}
	set queue to {makeTask("fetch", 1, "data"), makeSquareTask(7), makeTask("flaky", 5, "never")}
	set end of queue to BaseTask
	set end of queue to makeTask("parse", 2, {1, 2, 3})
	
	set seenStatuses to current application's NSMutableOrderedSet's orderedSet()
	set summary to {}
	repeat while (count of queue) > 0
		set aTask to item 1 of queue
		set queue to rest of queue
		set outcome to runWithRetry(aTask)
		(seenStatuses's addObject:(status of outcome))
		if status of outcome is ok of statusNames then
			set completed to completed + 1
			set v to value of outcome
			if class of v is list then
				set v to "list of " & (count v)
			else if class of v is integer then
				set v to "int " & v
			end if
			set end of summary to (taskName of aTask) & ":" & v & " after " & (tries of outcome)
		else
			set end of summary to (taskName of aTask) & ":gave up after " & (tries of outcome)
		end if
	end repeat
	
	set statuses to (seenStatuses's array()) as list
	return joinList(summary, "; ") & " | " & completed & " done | " & joinList(statuses, ",") & " | " & joinList(attemptLog, " ")
end run

