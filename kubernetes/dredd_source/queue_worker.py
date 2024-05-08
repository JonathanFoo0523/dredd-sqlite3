from runner.dredd_source.worker import DreddAndCompileWorker

import boto3
import json
import argparse
from pathlib import Path
from os import mkdir
from os.path import isdir

# expected arguments 
parser = argparse.ArgumentParser(description='Apply mutation to file and compile.')
parser.add_argument("dredd_src_path",
                        help="Directory containing dredd binary, and clang tool associated with it.",
                        type=Path)
parser.add_argument("sqlite_src_path",
                    help="Directory containing sqlite3 source file and test file",
                    type=Path)
parser.add_argument("output_directory",
                    help="Directory to score binary of mutated file, binary of mutant coverage, and mutant info file",
                    type=Path)
args = parser.parse_args()

if isdir(args.output_directory):
        print(f"Replacing content in {args.output_directory}")
else:
    mkdir(args.output_directory)

# Create worker for dredd and compile task
worker = DreddAndCompileWorker(args.dredd_src_path, args.sqlite_src_path, args.output_directory)

# Create SQS client
sqs = boto3.client('sqs')


# Get URL for dredd souce SQS queue
response = sqs.get_queue_url(QueueName='dredd-source-queue')
dredd_source_queue_url = response['QueueUrl']
print("dredd_source_queue_url:", dredd_source_queue_url)

# Get URL for dredd test SQS queue
response = sqs.get_queue_url(QueueName='dredd-test-queue')
dredd_test_queue_url = response['QueueUrl']
print("dredd_test_queue_url:", dredd_test_queue_url)

while True:
    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=dredd_source_queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=300,
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
        target = obj['target']
    except:
        print("Message can't be parse in expected format")
        sqs.delete_message(QueueUrl=dredd_source_queue_url,ReceiptHandle=receipt_handle)
        continue


    print("Working on:", file, target)
    worker.run(file, target)

    # # argument for MutationTestingWorker, assume binary is defoned in /sample_binary
    # coverage_bin = f'{args.binary_dir}/testfixture_{file}_coverage'
    # mutation_bin = f'{args.binary_dir}/testfixture_{file}_mutation'
    # mutation_info = f'{args.binary_dir}/{file}_mutation_info.json'

    # process the work queue
    # asyncio.run(MutationTestingWorker(file, coverage_bin, mutation_bin, mutation_info, args.output_dir).async_slice_runner(tests))

    # Delete received message from queue
    sqs.delete_message(QueueUrl=dredd_source_queue_url,ReceiptHandle=receipt_handle)

    # Add message to next pipeline
    sqs.send_message(QueueUrl=dredd_test_queue_url, MessageBody=json.dumps({"file": file}))
