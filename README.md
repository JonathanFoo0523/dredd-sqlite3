# dredd-sqlite3
Using Dredd mutation testing framework to generate test cases that improve mutation coverage of sqlite3

## Requirements
### Install dredd
At suitable directory, run the following command. Change `clang+llvm-{VERSION}-{TARRGET}` as required at 2 places.
```shell
# Clone dredd
git clone --recursive https://github.com/mc-imperial/dredd.git
cd dredd

# Install Clang/LLVM
cd third_party
curl -Lo clang+llvm.tar.xz https://github.com/llvm/llvm-project/releases/download/llvmorg-16.0.0/clang+llvm-16.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz
tar xf clang+llvm.tar.xz
rm clang+llvm
mv clang+llvm-16.0.0-x86_64-linux-gnu-ubuntu-18.04 clang+llvm
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
### Install SQLancer
### Install CReduce

### Install pip requirements
```shell
pip install -r requirements.txt
```

## Usage

## Understanding Outputs

## Result

