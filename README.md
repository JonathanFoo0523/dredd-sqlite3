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
CC=${DREDD_CHECKOUT}/third_party/clang+llvm/bin/clang CFLAGS='-MJ cd.json -Wno-everything' ./configure
make .target_source # This create directory containing all source files for sqlite3.c
```

Modify Makefile so `sqlite` and `testfixture` share the same compilation flag. Add this to last moditication of `SHELL_OPT`.
```
SHELL_OPT = -DSQLITE_NO_SYNC=1 $(TEMP_STORE) $(TESTFIXTURE_FLAGS)
```

### Install SQLancer
At suitable directory, run the following command. Refer to installation instruction [here](https://github.com/sqlancer/sqlancer).
```shell
sudo apt install maven # (Optional) Required Package

git clone https://github.com/sqlancer/sqlancer.git
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

## Understanding Outputs

## Result
