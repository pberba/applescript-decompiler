-- test: xfail record labels that are keywords or need |bars|
set r to {a:1, b:2, |weird name|:3, name:4}
return r
