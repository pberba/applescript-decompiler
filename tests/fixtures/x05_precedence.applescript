set x to 2
set y to x div 2 + (x mod 2) * (x - 1) / (3 ^ 2)
set z to (x > 1 and x < 3) or not (x = 2)
set s to "a" & "b" & "c"
set b to x ≥ 1 and (x ≤ 2 or x is not 3)
return {y, z, s, b}

