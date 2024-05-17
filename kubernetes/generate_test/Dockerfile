FROM python:latest

# COPY queue_worker.py .
# COPY test_list.txt .
COPY requirements.txt .
COPY temp_main.py .

RUN pip install boto3
RUN pip install -i https://test.pypi.org/simple/ dredd-sqlite3
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "temp_main.py" ]
CMD ["/test_list.txt", "/sample_output"]

