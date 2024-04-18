#!/bin/sh
SOURCE_FILE=$(ls tsrc/*.c)

for file in ${SOURCE_FILE}
do
    FILE_C=$(echo $file | cut -d/ -f2)
    FILE_NAME=$(echo $FILE_C | cut -d. -f1)

    echo $FILE_NAME

    if test "$FILE_NAME" = "geopoly" || test "$FILE_NAME" = "alter"; then
        continue
    fi
    
    # Keep a clean copy of file
    cp $file sample_mutation_clean/$FILE_C

    # Apply mutation to file, output testfixture_${FILE_NAME}_mutations
    ${DREDD_EXECUTABLE} $file --mutation-info-file sample_mutation_res/${FILE_NAME}_mutation_info.json
    tclsh tool/mksqlite3c.tcl
    echo 'Compiling testfixture_mutation'
    make testfixture >/dev/null
    mv testfixture testfixture_${FILE_NAME}_mutations

    # Reset file
    cp sample_mutation_clean/$FILE_C $file

    # Apply mutant_tracking to file, output testfixture_${FILE_NAME}_tracking
    ${DREDD_EXECUTABLE} --only-track-mutant-coverage $file --mutation-info-file temp.json
    tclsh tool/mksqlite3c.tcl
    echo 'Compiling testfixture_coverage'
    make testfixture >/dev/null
    mv testfixture testfixture_${FILE_NAME}_tracking

    # Reset file
    cp sample_mutation_clean/$FILE_C $file

    # Perform Mutation Testing, output list of killed mutants
    python3 sampleMutation.py ./testfixture_${FILE_NAME}_mutations ./testfixture_${FILE_NAME}_tracking ss_tests.txt \
        -o sample_mutation_res/${FILE_NAME}_output.csv -k sample_mutation_res/${FILE_NAME}_killed.txt

    # Archive
    mv testfixture_${FILE_NAME}_mutations sample_mutation_res/testfixture_${FILE_NAME}_mutations
    mv testfixture_${FILE_NAME}_tracking sample_mutation_res/testfixture_${FILE_NAME}_tracking
    
done