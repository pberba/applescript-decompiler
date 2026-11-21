-- test: no-run
-- test: xfail the last statement's assignment is lost (`set y to 3` becomes `return 3`)
display dialog "hi" buttons {"OK"} default button 1
set y to 3
