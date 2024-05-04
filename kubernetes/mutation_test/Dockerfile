FROM python:latest

RUN pip install boto3
RUN pip install -i https://test.pypi.org/simple/ dredd-sqlite3

COPY queue_worker.py .
COPY test_list.txt .
COPY requirements.txt .

RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "queue_worker.py" ]
CMD ["/sample_binary", "/sample_output"]