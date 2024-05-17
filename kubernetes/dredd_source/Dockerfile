# FROM ubuntu:22.04

# RUN apt-get update
# RUN apt-get install -y --no-install-recommends tcl && apt-get install -y tcl8.6-dev
# RUN apt-get update && apt-get install -y build-essential libtinfo5

# COPY temp.sh /home/temp.sh

# RUN chmod +x /home/temp.sh
# WORKDIR /home/sqlite-src
# CMD [ "/home/temp.sh" ]

FROM python:latest

# COPY dredd /home/dredd/.
# COPY sqlite-src /home/sqlite-src/.
# COPY dredd_source.sh /home/dredd_source.sh

COPY queue_worker.py .
COPY requirements.txt .

RUN pip install boto3
RUN pip install -i https://test.pypi.org/simple/ dredd-sqlite3
RUN pip install -r requirements.txt


ENV DREDD_CHECKOUT=/home/dredd
ENV DREDD_CLANG_BIN_DIR=${DREDD_CHECKOUT}/third_party/clang+llvm/bin
ENV DREDD_EXECUTABLE=${DREDD_CLANG_BIN_DIR}/dredd
ENV CC=${DREDD_CLANG_BIN_DIR}/clang
ENV CFLAGS='-MJ cd.json'

RUN apt-get update && apt-get install -y build-essential libtinfo5

# ENV DEBIAN_FRONTEND=noninteractive
# RUN apt-get install -y --no-install-recommends tcl && apt-get install -y tcl8.6-dev

# WORKDIR /home/sqlite-src
# RUN echo $(pwd)
# RUN ${DREDD_CLANG_BIN_DIR}/clang --version
# RUN ./configure 
# RUN make .target_source

ENTRYPOINT [ "python", "-u", "queue_worker.py" ]
CMD [ "/required_tools/dredd", "/required_tools/sqlite-src", "/sample_binary" ]
