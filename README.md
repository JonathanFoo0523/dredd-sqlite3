# dredd-sqlite3
Using Dredd mutation testing framework to generate test cases that improve mutation coverage of sqlite3

## Requirements
### Install dredd
At suitable directory, run the following command. Change `clang+llvm-*-*` as required. Refer to installation instruction [here](https://github.com/mc-imperial/dredd).
```shell
# (Optional) Required Package
sudo apt install build-essential libghc-terminfo-dev libzstd-dev zlib1g-dev cmake ninja-build

# Clone dredd
git clone --recursive https://github.com/mc-imperial/dredd.git
cd dredd

# Install Clang/LLVM
cd third_party
curl -Lo clang+llvm.tar.xz https://github.com/llvm/llvm-project/releases/download/llvmorg-16.0.4/clang+llvm-16.0.4-x86_64-linux-gnu-ubuntu-22.04.tar.xz
tar xf clang+llvm.tar.xz
rm -r clang+llvm
mv clang+llvm-16.0.4-x86_64-linux-gnu-ubuntu-22.04 clang+llvm
rm clang+llvm.tar.xz
cd ..

# Build
mkdir build && cd build
cmake -G Ninja .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
cp src/dredd/dredd ../third_party/clang+llvm/bin
```
Export the path to dredd:
```shell
export DREDD_CHECKOUT=/path/to/dredd
```
### Install SQLite3
Install the complete(raw) source tree instead of amalgation source code:
```shell
sudo apt install unzip tcl8.6-dev # Required Package

curl -Lo sqlite-src-3450100.zip https://www.sqlite.org/2024/sqlite-src-3450100.zip
unzip sqlite-src-3450100.zip
mv sqlite-src-3450100 sqlite-src
rm sqlite-src-3450100.zip
```
Export the path to sqlite source:
```shell
export SQLITE_SRC_CHECKOUT=/path/to/sqlite-src
```
Configure and Make
```shell
cd sqlite-src

# Configure to enable fts, rtree, update limit
CC=${DREDD_CHECKOUT}/third_party/clang+llvm/bin/clang CFLAGS='-MJ cd.json -Wno-everything' ./configure --enable-fts3 --enable-fts4 --enable-fts5 --enable-rtree --enable-update-limit
make .target_source # This create directory containing all source files for sqlite3.c
```

Modify Makefile so `sqlite` and `testfixture` share the same compilation flag. Add this to last moditication of `SHELL_OPT`.
```
SHELL_OPT = -DSQLITE_NO_SYNC=1 $(TEMP_STORE) $(TESTFIXTURE_FLAGS) $(LIBTCL) ext/fts3/fts3_term.c
```

### Install SQLancer
At suitable directory, run the following command. Refer to installation instruction [here](https://github.com/sqlancer/sqlancer).
```shell
sudo apt install maven # (Optional) Required Package

git clone https://github.com/JonathanFoo0523/sqlancer.git
cd sqlancer
mvn package -DskipTests
```
Export the jar file in target. Replace `sqlancer-*.jar` with build version as necessary.
```shell
export SQLANCER_JAR=/path/to/sqlancer/target/sqlancer-2.0.0.jar
```

### Install CReduce
Ubuntu, Debian, Gentoo, FreeBSD and Mac OS X comes with precompiled package for CReduce. Otherwise, CReduce can be build from source. Refer to installation instruction [here](https://github.com/csmith-project/creduce/blob/master/INSTALL.md).
```
sudo apt install creduce
export CREDUCE_EXECUTABLE=/usr/bin/creduce
```


### Install pip requirements
```shell
pip install -r requirements.txt
```

## Usage
### Applying Dredd to Source
```shell
python3 -m runner.dredd_source.main ${DREDD_CHECKOUT} ${SQLITE_SRC_CHECKOUT} ${DREDD_OUTPUT_PATH}
```
### Mutation Testing
```shell
python3 -m runner.dredd_test.main ${DREDD_CHECKOUT} ${SQLITE_SRC_CHECKOUT} ${DREDD_OUTPUT_PATH} ${MUTATION_OUTPUT_PATH}
```
### Fuzz Surviving Mutants
```shell
python3 -m runner.generate_test.main ${SQLANCER_JAR} ${DREDD_OUTPUT_PATH} ${MUTATION_OUTPUT_PATH} ${FUZZ_OUTPUT_PATH}
```
### Reduce Test Case
```shell
python3 -m runner.reduce_test.main ${DREDD_OUTPUT_PATH} ${FUZZ_OUTPUT_PATH} ${REDUCTION_OUTPUT_PATH}
```
### Package Resuced Test Case
```shell
python3 -m runner.reduce_test.main ${DREDD_OUTPUT_PATH} ${REDUCTION_OUTPUT_PATH} ${TCLIFY_OUTPUT_PATH}
```
Ensure that `${TCLIFY_OUTPUT_PATH}` contains the `*.tcl` file from `sqlite-src/test/*.tcl` before tunning the `testfixture` on `${TCLIFY_OUTPUT_PATH}`


## Understanding Sample Outputs
### Extension Above Enabled
`sample_dredd_output_all`: Contains binary of `testfixture`, `sqlite3` after applying Dredd on slite3 source

`sample_regression_output_all`: Conntains result of mutation testing on extraquick, quick, full subset of TCL test.

`sample_fuzzing_output_*`: Contains result of mutants fuzzing with random, NoRec, TlP oracle of sqlancer.

`sample_reduction_output_*`: Contains result of test case reduction with random, NoRec, TLP oracle of sqlancer. 

`sample_tclify_output_*`: Contains result of packaged TCL test for corresponding oracle.

### No Optional Extension enabled
Results of running the worflow with no extension enabled can be found in directory `sample_fuzzing_output`, `sample_redction_output`, `sample_tclify_output`.

