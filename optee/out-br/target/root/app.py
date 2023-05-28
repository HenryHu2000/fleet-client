from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import KafkaError
from kafka.structs import TopicPartition
import json
import logging
import base64
import subprocess
import shlex
import re
import uuid
import os
import uuid
from datetime import datetime, timezone

def load_counter():
    if not os.path.exists('counters.dat'):
        return 0
    with open('counters.dat', mode='r') as f:
        return int(f.read())

def store_counter(value):
    with open('counters.dat', mode='w') as f:
        f.write(str(value))

def on_send_success(record_metadata):
    print(record_metadata.topic)
    print(record_metadata.partition)
    print(record_metadata.offset)

def on_send_error(excp):
    logging.error('I am an errback', exc_info=excp)
    # handle exception

def main():
    servers = ['pkc-41mxj.uksouth.azure.confluent.cloud:9092']
    username = 'username'
    password = 'password'
    mac_addr = ':'.join(re.findall('..', '%012x' % uuid.getnode()))

    # consume earliest available messages, don't commit offsets
    consumer = KafkaConsumer('todo-tasks',
                             group_id='fltee-client' + '-' + mac_addr,
                             bootstrap_servers=servers, 
                             value_deserializer=lambda m: json.loads(m.decode('ascii')), 
                             auto_offset_reset='earliest', 
                             enable_auto_commit=True,
                             security_protocol="SASL_SSL",
                             sasl_mechanism='PLAIN',
                             sasl_plain_username=username,
                             sasl_plain_password=password)
    # produce json messages
    producer = KafkaProducer(bootstrap_servers=servers, 
                             value_serializer=lambda m: json.dumps(m).encode('ascii'), 
                             retries=5,
                             security_protocol="SASL_SSL",
                             sasl_mechanism='PLAIN',
                             sasl_plain_username=username,
                             sasl_plain_password=password)

    counter = load_counter()
    print("============= poll global model =============")
    for message in consumer:
        print("%s:%d:%d: key=%s" % (message.topic, message.partition,
                                              message.offset, message.key))
        partition = TopicPartition(message.topic, message.partition)
        highwater = consumer.highwater(partition)
        consumer.seek(partition, highwater - 1)
        if highwater - message.offset > 1:
            continue
        print("============= start local training =============")
        supertask = message.value
        date_created = datetime.now(tz=timezone.utc).isoformat(timespec='milliseconds')
        with open("/root/models/mnist/mnist_lenet_global.weights_ree", "wb") as file:
            file.write(base64.b64decode(supertask['inputModels'][0]['ree'].encode("ascii")))
        with open("/root/models/mnist/mnist_lenet_global.weights_tee", "wb") as file:
            file.write(base64.b64decode(supertask['inputModels'][0]['tee'].encode("ascii")))
        command = 'darknetp classifier train -pp_start 6 -pp_end 8 -ss 1 "cfg/mnist.dataset" "cfg/mnist_lenet.cfg" "models/mnist/mnist_lenet_global.weights"'
        subprocess.call(shlex.split(command), cwd="/root/")
        print("============= offer local model =============")
        counter += 1
        store_counter(counter)

        with open("/root/tmp/backup/mnist_lenet.weights_ree", "rb") as ree_file, open("/root/tmp/backup/mnist_lenet.weights_tee", "rb") as tee_file:
            ree_base64 = base64.b64encode(ree_file.read()).decode("ascii")
            tee_base64 = base64.b64encode(tee_file.read()).decode("ascii")
            local_model = {'id': str(uuid.uuid4()), 'ree': ree_base64, 'tee': tee_base64}
            completed_task = {'id': str(uuid.uuid4()), 'dateCreated': date_created, 'taskType': 'TRAINING', 'taskStatus': 'COMPLETED', 'supertask': {'id': supertask['id']}, 'outputModels': [local_model]}
            producer.send('done-tasks', completed_task).add_callback(on_send_success).add_errback(on_send_error)

        # block until all async messages are sent
        producer.flush()

        print("============= poll global model =============")

if __name__ == '__main__':
    main()
