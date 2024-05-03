#!/bin/sh

SOURCE_FILE=$(cd ${SQLITE_SRC_CHECKOUT} && ls tsrc/*.c)
TARGETS="testfixture sqlite3"

for target in ${TARGETS}
do
    for file in ${SOURCE_FILE} 
    do
        FILE_C=$(echo $file | cut -d/ -f2)
        FILE_NAME=$(echo $FILE_C | cut -d. -f1)
        SAN_FILE_NAME=$(echo $FILE_NAME | sed "s/_/-/g")
	TARGET=$target
	
	if test "$FILE_NAME" = "tclsqlite" || test "$FILE_NAME" = "shell" || test "$FILE_NAME" = "userauth" || test "$FILE_NAME" = "geopoly"
	then
		continue
	fi
		
        cat job-tmpl.yaml | sed -e "s/\$FILE/$FILE_NAME/" -e "s/\$TARGET/$TARGET/" -e "s/\$SANFILE/$SAN_FILE_NAME/" > jobs/job-$SAN_FILE_NAME-$TARGET.yaml

done
done
