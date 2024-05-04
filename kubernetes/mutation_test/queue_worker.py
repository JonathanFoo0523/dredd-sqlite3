from runner.dredd_test.worker import MutationTestingWorker

import boto3
import asyncio
import json
import argparse
from pathlib import Path

# expected arguments 
parser = argparse.ArgumentParser(description='Apply mutation to file.')
parser.add_argument('binary_dir', help='Directory that contains testfixture mutated binary, coverage binary and mutation-info-file.', type=Path)
parser.add_argument('output_dir', help='Directory to store result of mutation testing.', type=Path)
args = parser.parse_args()

with open('test_list.txt', 'r') as test_list:
    tests = ['/home/ubuntu/sqlite-src/' + line.rstrip('\n') for line in test_list]

# Create SQS client
sqs = boto3.client('sqs')

# Get URL for SQS queue
response = sqs.get_queue_url(QueueName='dredd-source-queue')
queue_url = response['QueueUrl']
print("queue_url:", queue_url)

while True:
    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
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
        print("Message can;t be parse in expected format")
        continue

    # argument for MutationTestingWorker, assume binary is defoned in /sample_binary
    coverage_bin = f'{args.binary_dir}/testfixture_{file}_coverage'
    mutation_bin = f'{args.binary_dir}/testfixture_{file}_mutation'
    mutation_info = f'{args.binary_dir}/{file}_mutation_info.json'

    # process the work queue
    asyncio.run(MutationTestingWorker(file, coverage_bin, mutation_bin, mutation_info, args.output_dir).async_slice_runner(tests))

    # Delete received message from queue
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )
