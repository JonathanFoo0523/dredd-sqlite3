## Extract test from sqlite3 test suite

### Example Usage
```SHELL
export TEST_SUBSET=veryquick
$SQLITE_SRC_CHECKOUT/testfixture $SQLITE_SRC_CHECKOUT/test/$TEST_SUBSET.test --verbose=0 > "$TEST_SUBSET"_output.txt 
python3 extract_test.py $SQLITE_SRC_CHECKOUT "$TEST_SUBSET"_output.txt "$TEST_SUBSET"_duration_sorted.txt duration
```

### Checked test subset (Provided in the same directory)
```
extraquick.test
veryquick.test
quick.test
```



