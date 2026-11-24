set b to application "Finder" is running
if application "Terminal" is not running then set b to false
set progress total steps to 3
set progress completed steps to 1
set progress description to "Installing"
set progress additional description to "Step 1"
return {b, progress total steps}

