set result to 5
set x to result + 1
set result to display dialog "Continue?" buttons {"OK"}
set b to button returned of result
return {x, b}

