#!/bin/sh

set -e 

FILE_C=$(echo $file | cut -d/ -f2)
FILE_NAME=$(echo $FILE_C | cut -d. -f1)
TARGET=$(echo $target)

echo $FILE_NAME $TARGET


# Keep a clean copy of file
cp $file clean_$FILE_C

echo $file
echo ${DREDD_EXECUTABLE}

# Preparing compilation database
echo "Preparing compilation database"
CC_FLAGS="-MJ cd.json" make ${TARGET}
make ${TARGET}
sed -e '1s/^/[\n/' -e '$s/,$/\n]/' cd.json > compile_commands.json

# Apply mutation to file, output ${TARGET}_${FILE_NAME}_mutations
echo "Mutated and compile file"
${DREDD_EXECUTABLE} $file --mutation-info-file /sample_binary/${FILE_NAME}_${TARGET}_info.json
tclsh tool/mksqlite3c.tcl
make ${TARGET}
mv testfixture ${TARGET}_${FILE_NAME}_mutations

# Reset file
cp clean_$FILE_C $file

# Apply mutant_tracking to file, output ${TARGET}_${FILE_NAME}_tracking
echo "Apply coverage and compile file"
${DREDD_EXECUTABLE} --only-track-mutant-coverage $file --mutation-info-file /sample_binary/${FILE_NAME}_${TARGET}_info.json
tclsh tool/mksqlite3c.tcl
make testfixture
mv testfixture ${TARGET}_${FILE_NAME}_tracking

# Archive
mv ${TARGET}_${FILE_NAME}_mutations /sample_binary/${TARGET}_${FILE_NAME}_mutations
mv ${TARGET}_${FILE_NAME}_tracking /sample_binary/${TARGET}_${FILE_NAME}_tracking

echo "Done"
