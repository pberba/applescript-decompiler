use AppleScript version "2.4"
use framework "Foundation"
use scripting additions
set s to current application's NSString's stringWithString:"hello"
set u to (s's uppercaseString()) as text
set arr to current application's NSArray's arrayWithArray:{3, 1, 2}
set srt to (arr's sortedArrayUsingSelector:"compare:") as list
return {u, srt}

