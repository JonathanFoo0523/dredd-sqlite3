FROM python:latest

RUN pip install boto3
RUN pip install -i https://test.pypi.org/simple/ dredd-sqlite3

COPY queue_worker.py .
COPY test_list.txt .

CMD [ "python", "queue_worker.py" ]