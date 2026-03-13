# Fix fetch: the pinned SRCREV is on branch 'poco-1.12.5', not 'master'
SRC_URI:remove = "git://github.com/pocoproject/poco.git;branch=master;protocol=https"
SRC_URI:append = " git://github.com/pocoproject/poco.git;branch=poco-1.12.5;protocol=https"
