-- test: xfail properties of a script defined inside a handler are lost
on mk(k)
script T
property c : k
property d : {1, "a"}
on getc()
return c + 1
end getc
set c to 9
end script
return T
end mk
return mk(3)'s getc()
