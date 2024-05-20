## Extract test from sqlite3 test suite

### Example Usage
```SHELL
export TEST_SUBSET=veryquick
$SQLITE_SRC_CHECKOUT/testfixture $SQLITE_SRC_CHECKOUT/test/testrunner.tcl $TEST_SUBSET
python3 extract_test.py testrunner.log "$TEST_SUBSET"_testlist.txt duration

# cleanup
rm -r testdir*
rm testrunner.log testrunner.db
```

### Available testsubset
```
extraquick
veryquick
quick
full
```



