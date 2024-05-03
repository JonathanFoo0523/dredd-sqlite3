FROM ubuntu:22.04

COPY dredd /home/dredd/.
COPY sqlite-src /home/sqlite-src/.
COPY dredd_source.sh /home/dredd_source.sh

ENV DREDD_CHECKOUT=/home/dredd
ENV DREDD_CLANG_BIN_DIR=${DREDD_CHECKOUT}/third_party/clang+llvm/bin
ENV DREDD_EXECUTABLE=${DREDD_CLANG_BIN_DIR}/dredd
ENV CC=${DREDD_CLANG_BIN_DIR}/clang
ENV CFLAGS='-MJ cd.json'

RUN apt-get update && apt-get install -y build-essential libtinfo5

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y --no-install-recommends tcl && apt-get install -y tcl8.6-dev

WORKDIR /home/sqlite-src
RUN echo $(pwd)
RUN ${DREDD_CLANG_BIN_DIR}/clang --version
RUN ./configure 
RUN make .target_source

RUN echo "$file"
RUN echo "$target"

ENTRYPOINT [ "/home/dredd_source.sh" ]
