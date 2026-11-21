-- test: xfail string properties, `global` declarations and `my` are lost
property a : 1
property b : "x"
global g1, g2
script Inner
property c : 5
end script
set g1 to a & b
return {Inner's c, g1, my a}
