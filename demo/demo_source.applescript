(*
    Sample AppleScript for disassembler testing
    - Contains handlers
    - Uses Finder and System Events
    - Has basic string "obfuscation"
*)

-- Entry point

property current_prefix : "LOG: "


on run
	set other_script to load script POSIX file "/path/to/Logger.scpt"
	other_script's logMessage("Hello")
	my logMessage("Starting demo script…")
	my logMessage(current_prefix)
	my logMessage(current_prefix2)
	my logMessage(current_prefix)
	
	-- Do some fake environment checks
	set envInfo to my collectEnvironmentInfo()
	my logMessage("Collected environment info: " & (envInfo as string))
	
	-- Use basic "obfuscation" to build a command string
	set obfuscated to {"do", " ", "she", "ll", " ", "sc", "ri", "pt", " \"ec", "ho", " \"\"He", "llo", " fr", "om", " obf", "usc", "at", "ed", " co", "mm", "an", "d\"\"\""}
	set cmd to my deobfuscateStringList(obfuscated)
	
	my logMessage("About to run (safe) obfuscated command…")
	
	try
		set cmdResult to do shell script cmd
		my logMessage("Command result: " & cmdResult)
	on error errMsg number errNum
		my logMessage("Error running shell command: " & errMsg & " (" & errNum & ")")
	end try
	
	
	try
		set cmdResult to do shell script cmd
		my logMessage("Another command result: " & cmdResult)
		(1 + 2)
		-(1 ^ 5) / 3
		set temp to not (1 < 2)
		my logMessage("Another command result: " & cmdResult)
		my logMessage("Not last command result: " & cmdResult)
	end try
	
	
	try
		set cmdResult to do shell script cmd
		my logMessage("Last Command result: " & cmdResult)
	on error errMsg
		my logMessage("Error running shell command: " & errMsg & " (" & ")")
		my finderDemo()
	end try
	
	-- Demonstrate Finder usage
	my finderDemo()
	
	-- Demonstrate System Events usage
	my systemEventsDemo()
	systemEventsDemo()
	
	logMessage("Demo script finished.")
	otherlogger's logMessage("Demo script finished.")
end run

property current_prefix2 : "Other LOG: "

-- Collect a few pieces of environment info as a record
on collectEnvironmentInfo()
	set hostName to do shell script "scutil --get LocalHostName || hostname"
	set userName to (system attribute "USER")
	set homePath to (system attribute "HOME")
	
	set infoRecord to {hostName:hostName, userName:userName, homePath:homePath}
	return infoRecord
end collectEnvironmentInfo


-- Very basic "deobfuscation": join previously split string fragments
on deobfuscateStringList(fragmentList)
	set finalText to ""
	repeat with fragment in fragmentList
		set finalText to finalText & fragment
	end repeat
	return finalText
end deobfuscateStringList

on demoRepeats()
	log "=== repeat \"forever\"==="
	repeat
		set counter to counter + 1
		log "counter = " & counter
		if counter > 5 then exit repeat
	end repeat
	
	
	log "=== repeat n times ==="
	repeat 3 times
		log "Hello!"
	end repeat
	
	
	log "=== repeat while ==="
	set counter to 1
	repeat while counter ≤ 3
		log "Counter is " & counter
		set counter to counter + 1
	end repeat
	
	
	log "=== repeat until ==="
	set done to false
	set countUp to 0
	repeat until done
		set countUp to countUp + 1
		log "CountUp is " & countUp
		if countUp ≥ 3 then set done to true
	end repeat
	
	
	log "=== repeat with i from a to b ==="
	repeat with i from 1 to 3
		log "i = " & i
	end repeat
	
	
	log "=== repeat with i from a to b by step ==="
	repeat with i from 0 to 6 by 2
		log "i (step 2) = " & i
	end repeat
	
	
	log "=== repeat with item in list ==="
	set fruits to {"apple", "banana", "orange"}
	repeat with f in fruits
		log "Fruit = " & (contents of f)
	end repeat
	
	
	log "=== repeat with exit repeat ==="
	set x to 1
	repeat
		if x > 3 then exit repeat
		log "x = " & x
		set x to x + 1
	end repeat
	
	
	log "=== nested repeats ==="
	repeat with a from 1 to 2
		repeat with b from 1 to 2
			repeat with c from 1 to 2
				log "a=" & a & ", b=" & b
			end repeat
		end repeat
	end repeat
	
	
end demoRepeats



on demoIfStatements()
	
	log "=== Basic IF ==="
	set x to 10
	if x > 5 then
		log "x is greater than 5"
	end if
	
	
	log "=== IF…ELSE ==="
	set x to 3
	if x > 5 then
		log "x is greater than 5"
	else
		log "x is NOT greater than 5"
	end if
	
	
	log "=== IF…ELSE IF…ELSE chain ==="
	set score to 85
	if score ≥ 90 then
		log "Grade: A"
	else if score ≥ 80 then
		log "Grade: B"
	else if score ≥ 70 then
		log "Grade: C"
	else
		log "Grade: F"
	end if
	
	
	log "=== One-line IF ==="
	if 2 + 2 = 4 then log "Math works!"
	
	log "=== IF with AND/OR ==="
	set age to 20
	if age ≥ 18 and age ≤ 30 then
		log "Young adult"
	end if
	
	if age < 0 or age > 120 then
		log "Invalid age"
	end if
	
	
	log "=== IF inside a loop ==="
	repeat with n from 1 to 5
		if n mod 2 = 0 then
			log n & " is even"
		else
			log n & " is odd"
		end if
	end repeat
	
	
	log "=== IF checking list contents ==="
	set fruits to {"apple", "orange", "grape"}
	if fruits contains "orange" then
		log "We have an orange!"
	else
		log "No orange found."
	end if
	
	log "=== Nested IF blocks ==="
	set x to 10
	set y to 5
	if x > 0 then
		if y > 0 then
			log "Both numbers are positive"
		end if
	end if
	
	
end demoIfStatements






-- More contrived obfuscation using character codes and an offset
on decodeWithOffset(codeList, off)
	set outputText to ""
	repeat with c in codeList
		set outputText to outputText & (character id of ((c as integer) - (off)))
	end repeat
	1 + 1
	return outputText
end decodeWithOffset



on get_url()
	return (ASCII character 104) & (ASCII character 116) & (ASCII character 116) & (ASCII character 112) & (ASCII character 58) & (ASCII character 47) & (ASCII character 47)
end get_url

-- Finder usage demo
on finderDemo()
	tell application "Terminal"
		
	end tell
	tell application "Finder"
		activate
		
		-- Get the desktop folder and count items
		set desktopFolder to desktop as alias
		set itemCount to count items of desktopFolder
		
		my logMessage("Finder: there are " & itemCount & " item(s) on the Desktop.")
		
		-- Create a small temporary folder on Desktop (if it doesn’t already exist)
		set tempFolderName to "AS_Disassembler_Test"
		if not (exists folder tempFolderName of desktopFolder) then
			make new folder at desktopFolder with properties {name:tempFolderName}
			my logMessage("Finder: created folder \"" & tempFolderName & "\" on Desktop.")
		else
			my logMessage("Finder: folder \"" & tempFolderName & "\" already exists.")
		end if

		-- Add nested
		get name extension of file "file.png" of folder "Downloads" of folder "Mary" of folder "Users" of startup disk
	end tell
end finderDemo


-- System Events usage demo
on systemEventsDemo()
	tell application "System Events"
		-- Get a list of running processes
		set procNames to name of every process
	end tell
	
	-- Take a few “interesting” ones (if present)
	set interestingNames to {}
	repeat with candidate in {"Finder", "Dock", "SystemUIServer", "Terminal"}
		if procNames contains candidate then
			set end of interestingNames to candidate
			return candidate
		end if
	end repeat
	
	if (count of interestingNames) is 0 then
		my logMessage("System Events: no interesting processes found (from our sample list).")
	else
		my logMessage("System Events: some running processes: " & (interestingNames as string))
	end if
	
	-- Show a small user-visible dialog (so you can see UI automation in logs)
	display dialog "Sample AppleScript for disassembler testing is running." buttons {"OK"} default button "OK" giving up after 5
end systemEventsDemo


-- Simple logger; uses 'run script' to create a dynamic message (to give you more AST structure)
on logMessage(msg)
	set timeStamp to do shell script "date '+%Y-%m-%d %H:%M:%S'"
	set assembled to "log \"[" & timeStamp & "] " & my escapeQuotes(msg) & "\""
	
	-- This `run script` indirection is intentional (more nodes in the compiled script)
	try
		run script assembled
	on error
		-- Fallback if 'log' is unavailable in some contexts
		display dialog "[" & timeStamp & "] " & msg buttons {"OK"} default button "OK" giving up after 3
	end try
end logMessage


-- Helper to escape quotes for embedding in dynamic code
on escapeQuotes(t)
	set AppleScript's text item delimiters to "\""
	set text item delimiters of AppleScript to "\""
	set parts to text items of t
	set AppleScript's text item delimiters to "\\\""
	set escaped to parts as string
	set AppleScript's text item delimiters to ""
	return escaped
end escapeQuotes


on rangeDemo()
	set myList to {10, 20, 30, 40, 50, 60}
	
	-- Get items 2 through 4 → {20, 30, 40}
	set subList to items 2 thru 4 of myList
	return subList
end rangeDemo


