-- Inventory report: parse CSV-ish text with Foundation, aggregate per
-- category with NSMutableDictionary, sort with NSSortDescriptor, and
-- format a report through script-object helpers.
use AppleScript version "2.4"
use framework "Foundation"
use scripting additions

property NSString : a reference to current application's NSString
property NSMutableDictionary : a reference to current application's NSMutableDictionary
property NSSortDescriptor : a reference to current application's NSSortDescriptor
property NSCharacterSet : a reference to current application's NSCharacterSet
property csvText : "sku,category,qty,price
A-100, tools ,3,4.50
A-101,tools,10,1.25
B-200,  garden,2,19.99
# comment line
B-201,garden,,7.00
C-300,kitchen,5,3.10
bad line
C-301,KITCHEN,1,12.00"
property reportTitle : "Inventory"

global warnings

-- A small logger; Reporter inherits from it and overrides `prefix`
script Logger
	property logLines : {}
	on prefix()
		return "log"
	end prefix
	on add(msg)
		set end of my logLines to (my prefix()) & ": " & msg
		return count of my logLines
	end add
	on dump()
		set AppleScript's text item delimiters to linefeed
		set out to logLines as text
		set AppleScript's text item delimiters to ""
		return out
	end dump
end script

script Reporter
	property parent : Logger
	on prefix()
		return "report/" & (continue prefix())
	end prefix
end script

on trimmed(s)
	set ws to NSCharacterSet's whitespaceAndNewlineCharacterSet()
	return ((NSString's stringWithString:s)'s stringByTrimmingCharactersInSet:ws) as text
end trimmed

on parseRecord(lineText, lineNumber)
	set fields to ((NSString's stringWithString:lineText)'s componentsSeparatedByString:",") as list
	if (count of fields) is not 4 then
		error "line " & lineNumber & ": expected 4 fields" number 501
	end if
	set qtyText to trimmed(item 3 of fields)
	if qtyText is "" then set qtyText to "0"
	try
		set qty to qtyText as integer
		set price to (trimmed(item 4 of fields)) as real
	on error errMsg number errNum
		error "line " & lineNumber & ": " & errMsg number 502
	end try
	return {sku:trimmed(item 1 of fields), category:(my lowercase(trimmed(item 2 of fields))), qty:qty, price:price}
end parseRecord

on lowercase(s)
	return ((NSString's stringWithString:s)'s lowercaseString()) as text
end lowercase

on aggregate(recs)
	set totals to NSMutableDictionary's dictionary()
	repeat with r in recs
		set cat to category of r
		set existing to (totals's objectForKey:cat)
		if existing is missing value then
			set existing to {0, 0}
		else
			set existing to existing as list
		end if
		set newQty to (item 1 of existing) + (qty of r)
		set newValue to (item 2 of existing) + (qty of r) * (price of r)
		(totals's setObject:{newQty, newValue} forKey:cat)
	end repeat
	return totals
end aggregate

on formatMoney(x)
	set cents to (round (x * 100) rounding as taught in school) as integer
	set whole to cents div 100
	set frac to cents mod 100
	if frac < 10 then
		set frac to "0" & frac
	end if
	return "$" & whole & "." & frac
end formatMoney

on run
	set warnings to 0
	set recs to {}
	set lineNumber to 0
	repeat with rawLine in paragraphs of csvText
		set lineNumber to lineNumber + 1
		set lineText to contents of rawLine
		if lineNumber is 1 or lineText starts with "#" then
			-- header and comments
		else
			try
				set end of recs to parseRecord(lineText, lineNumber)
			on error errMsg number errNum
				set warnings to warnings + 1
				Reporter's add("skip (" & errNum & ") " & errMsg)
			end try
		end if
	end repeat
	
	set totals to aggregate(recs)
	set keys to (totals's allKeys()) as list
	set sorter to NSSortDescriptor's sortDescriptorWithKey:"self" ascending:true selector:"compare:"
	set sortedKeys to ((current application's NSArray's arrayWithArray:keys)'s sortedArrayUsingDescriptors:{sorter}) as list
	
	set grand to 0
	repeat with k in sortedKeys
		set pair to (totals's objectForKey:k) as list
		set grand to grand + (item 2 of pair)
		tell Reporter to add((k as text) & " qty=" & (item 1 of pair) & " value=" & formatMoney(item 2 of pair))
	end repeat
	considering case
		if reportTitle is not "inventory" then Reporter's add("title=" & reportTitle)
	end considering
	Reporter's add("total=" & formatMoney(grand) & " warnings=" & warnings)
	return Reporter's dump()
end run

