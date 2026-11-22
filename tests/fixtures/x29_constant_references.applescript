set g to class of "x"
set f to {class of "x", class of 5, length of "abc"}
if class of "x" is text then set g to 1
return {g, f}

