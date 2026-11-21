-- JSON + regex pipeline: build nested records/lists, serialise with
-- NSJSONSerialization (sorted keys), parse back, walk the result
-- recursively, and pull numbers out of free text with NSRegularExpression.
use AppleScript version "2.4"
use framework "Foundation"
use scripting additions

property NSJSONSerialization : a reference to current application's NSJSONSerialization
property NSRegularExpression : a reference to current application's NSRegularExpression
property NSString : a reference to current application's NSString
property sortedKeysOption : 2 -- NSJSONWritingSortedKeys

on toJSON(value)
	set {theData, theError} to NSJSONSerialization's dataWithJSONObject:value options:sortedKeysOption |error|:(reference)
	if theData is missing value then error (theError's localizedDescription() as text) number 1001
	return (NSString's alloc()'s initWithData:theData encoding:4) as text
end toJSON

on fromJSON(jsonText)
	set theData to (NSString's stringWithString:jsonText)'s dataUsingEncoding:4
	set {obj, theError} to NSJSONSerialization's JSONObjectWithData:theData options:0 |error|:(reference)
	if obj is missing value then error "bad json" number 1002
	return obj as anything
end fromJSON

-- Recursively count leaves and sum every number found anywhere
on walk(node, depth)
	set leaves to 0
	set total to 0
	set deepest to depth
	if class of node is record then
		set node to (current application's NSDictionary's dictionaryWithDictionary:node)'s allValues() as list
	end if
	if class of node is list then
		repeat with child in node
			set {l, t, d} to walk(contents of child, depth + 1)
			set leaves to leaves + l
			set total to total + t
			if d > deepest then set deepest to d
		end repeat
	else
		set leaves to 1
		if class of node is in {integer, real} then set total to node
	end if
	return {leaves, total, deepest}
end walk

on extractNumbers(theText)
	set pattern to "(-?\\d+)(?:\\.(\\d+))?"
	set regex to NSRegularExpression's regularExpressionWithPattern:pattern options:0 |error|:(missing value)
	set str to NSString's stringWithString:theText
	set matches to regex's matchesInString:str options:0 range:{0, str's |length|()}
	set found to {}
	repeat with m in matches
		set end of found to (str's substringWithRange:(m's range())) as text
	end repeat
	return found
end extractNumbers

on run
	set config to {|name|:"pipeline", ver:3, enabled:true, stages:{{stepId:1, step:"load", file:{"a.csv", "b.csv"}}, {stepId:2, step:"clean", ratio:0.25}, {stepId:3, step:"store", target:{host:"db", port:5432}}}}
	set jsonText to toJSON(config)
	set parsed to fromJSON(jsonText)
	set {leafCount, numberSum, maxDepth} to walk(parsed, 0)
	
	-- text item delimiters vs regex
	set logText to "took 12 ms, retried -3 times, ratio 0.25, ids 7 8 9"
	set nums to extractNumbers(logText)
	set saved to AppleScript's text item delimiters
	set AppleScript's text item delimiters to ","
	set chunks to text items of logText
	set AppleScript's text item delimiters to "|"
	set rejoined to chunks as text
	set AppleScript's text item delimiters to saved
	
	set stageKinds to {}
	repeat with s in (stages of parsed)
		set end of stageKinds to step of s
	end repeat
	try
		fromJSON("{broken")
		set parseError to "none"
	on error errMsg number errNum
		set parseError to errNum
	end try
	return {length of jsonText, leafCount, numberSum, maxDepth, nums, rejoined, stageKinds, parseError, (character id 65) & (id of "z")}
end run

