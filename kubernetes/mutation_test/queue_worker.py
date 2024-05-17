from runner.dredd_test.worker import MutationTestingWorker

import boto3
import asyncio
import json
import argparse
from pathlib import Path
import os
from os.path import isdir, join, isfile

# expected arguments 
parser = argparse.ArgumentParser(description='Peform mutation testing on dredd-mutated binary.')
parser.add_argument("dredd_src_path",
                    help="Directory containing dredd binary, and clang tool associated with it.",
                    type=Path)
parser.add_argument("sqlite_src_path",
                    help="Directory containing sqlite3 source file and test file.",
                    type=Path)
parser.add_argument("test_files_path",
                    help="Files containing list of test file (eg: test/alter.test\n) to run mutation testing on.",
                    type=Path)
parser.add_argument("mutation_binary_path",
                    help="Directory containing binary of mutated file, binary of mutant coverage, and mutant info file",
                    type=Path)
parser.add_argument("output_directory",
                    help="Directory to result of mutation testing",
                    type=Path)
args = parser.parse_args()

if not isdir(args.output_directory):
    os.mkdir(args.output_directory)

with open(args.test_files_path, 'r') as test_files:
    tests = [os.path.join(args.sqlite_src_path, line.rstrip('\n')) for line in test_files]


# Create SQS client
sqs = boto3.client('sqs')

# Get URL for SQS test queue
response = sqs.get_queue_url(QueueName='dredd-test-queue-sample')
dredd_test_queue_url = response['QueueUrl']
print("dredd_test_queue_url:", dredd_test_queue_url)

# Get URL for dredd fuzz SQS queue
response = sqs.get_queue_url(QueueName='dredd-fuzz-queue')
dredd_test_fuzz_url = response['QueueUrl']
print("dredd_test_fuzz_url:", dredd_test_fuzz_url)

# class TimeoutExtender:
#     def __init__(self, period, queue_url):
#         self.time_since_reset = period
#         self.period = period
#         pass

#     def run(self):
#         pass


while True:
    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=dredd_test_queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=100,
        WaitTimeSeconds=20
    )


    if 'Messages' not in response:
        # queue is empty
        print("No Message")
        continue

    # Get the message (only one message is obtained as MaxNumberOfMessages=1)
    message = response['Messages'][0]
    receipt_handle = message['ReceiptHandle']
    try:
        obj = json.loads(message['Body'])
        file = obj['file']
    except:
        print("Message can't be parse in expected format")
        sqs.delete_message(QueueUrl=dredd_test_queue_url,ReceiptHandle=receipt_handle)
        continue

    # argument for MutationTestingWorker, assume binary is defined in /sample_binary
    file = file.split('.')[0]
    coverage_bin = os.path.join(args.mutation_binary_path, f'testfixture_{file}_coverage')
    mutation_bin = os.path.join(args.mutation_binary_path, f'testfixture_{file}_mutation')
    mutation_info = os.path.join(args.mutation_binary_path, f'{file}_testfixture_info.json')
    mutant_info_script = os.path.join(args.dredd_src_path, 'scripts', 'query_mutant_info.py')
    
    # process the work queue
    asyncio.run(MutationTestingWorker(mutant_info_script, file, coverage_bin, mutation_bin, mutation_info, args.output_directory).async_slice_runner(tests))

    # Delete received message from queue
    sqs.delete_message(QueueUrl=dredd_test_queue_url, ReceiptHandle=receipt_handle)

    # Add message to next pipeline
    sqs.send_message(QueueUrl=dredd_test_fuzz_url, MessageBody=json.dumps({"file": file}))
