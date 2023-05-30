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
import sys
from datetime import datetime, timezone
import http.client
import urllib
import getpass

def load_counter():
    if not os.path.exists('counters.dat'):
        return 0
    with open('counters.dat', mode='r') as f:
        return int(f.read())

def store_counter(value):
    with open('counters.dat', mode='w') as f:
        f.write(str(value))

def register(username, password):
    params = urllib.parse.urlencode({'username': username, 'password': password})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    conn = http.client.HTTPSConnection("fleet.haoweihu.com", 8443)
    conn.request("POST", "/api/public/register", params, headers)
    response = conn.getresponse()
    if response.status != 200:
        return None
    logging.info("%s %s" % (response.status, response.reason))
    data = response.read()
    conn.close()
    return json.loads(data.decode('ascii'))

def login(username, password):
    credentials = "Basic " + base64.b64encode((username + ":" + password).encode("ascii")).decode("ascii")
    headers = {"Accept": "application/json", "Authorization": credentials}
    conn = http.client.HTTPSConnection("fleet.haoweihu.com", 8443)
    conn.request("POST", "/api/users/me", headers=headers)
    response = conn.getresponse()
    if response.status != 200:
        return None
    logging.info("%s %s" % (response.status, response.reason))
    data = response.read()
    conn.close()
    return data.decode('ascii')

def diagnosis():
    logging.info('Running TEE diagnosis...')
    score = 0
    try:
        xtest_output = subprocess.check_output(['xtest'])
    except:
        pass
    else:
        score += 1
        if (b'subtests of which 0 failed' in xtest_output and b'test cases of which 0 failed' in xtest_output):
            score += 1
    logging.info('score=%s' % score)
    return score

def on_send_success(record_metadata):
    logging.info("%s:%d:%d" % (record_metadata.topic, record_metadata.partition,
                                      record_metadata.offset))

def on_send_error(excp):
    logging.error('Failed to send the local model!', exc_info=excp)
    # handle exception

def main():
    formatter = logging.Formatter("%(asctime)s %(levelname)s (%(threadName)s) %(message)s")
    logger = logging.getLogger()
    logger.level = logging.INFO
    fileHandler = logging.FileHandler("fleet.log")
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)
    
    servers = ['example.com:9092']
    username = 'username'
    password = 'password'
    mac_addr = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
    device_id = uuid.uuid3(uuid.UUID('00000000-0000-0000-0000-000000000000'), mac_addr)

    # consume earliest available messages, don't commit offsets
    consumer = KafkaConsumer('client-todo-tasks',
                             group_id='fleet-client' + '-' + mac_addr,
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
    max_retrains = 2
    retrain = 0
    last_offset = -1
    counter = load_counter()
    
    logging.info("============= poll global model =============")
    for message in consumer:
        logging.info("%s:%d:%d: key=%s" % (message.topic, message.partition,
                                              message.offset, message.key))
        partition = TopicPartition(message.topic, message.partition)
        highwater = consumer.highwater(partition)
        # Retrain
        if message.offset == last_offset:
            retrain += 1
        else:
            retrain = 0
        last_offset = message.offset
        if retrain < max_retrains - 1:
            consumer.seek(partition, highwater - 1)
        else:
            consumer.seek(partition, highwater)
        # Skip if model not the latest
        if highwater - message.offset > 1:
            continue
            
        logging.info("============= start local training =============")
        supertask = message.value
        date_created = datetime.now(tz=timezone.utc).isoformat(timespec='milliseconds')
        with open("/root/models/mnist/mnist_lenet_global.weights_ree", "wb") as file:
            file.write(base64.b64decode(supertask['inputModels'][0]['ree'].encode("ascii")))
        with open("/root/models/mnist/mnist_lenet_global.weights_tee", "wb") as file:
            file.write(base64.b64decode(supertask['inputModels'][0]['tee'].encode("ascii")))
        command = 'darknetp classifier train -pp_start 6 -pp_end 8 -ss 1 "cfg/mnist.dataset" "cfg/mnist_lenet.cfg" "models/mnist/mnist_lenet_global.weights"'
        process = subprocess.Popen(shlex.split(command), cwd="/root/", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with process.stdout:
            for line in iter(process.stdout.readline, b''):
                logging.info("%s" % line.decode("ascii").rstrip('\n'))
        exitcode = process.wait()
        logging.info('Process finished with exit code %d' % exitcode)
        
        logging.info("============= offer local model =============")
        counter += 1
        store_counter(counter)

        with open("/root/tmp/backup/mnist_lenet.weights_ree", "rb") as ree_file, open("/root/tmp/backup/mnist_lenet.weights_tee", "rb") as tee_file:
            ree_base64 = base64.b64encode(ree_file.read()).decode("ascii")
            tee_base64 = base64.b64encode(tee_file.read()).decode("ascii")
            local_model = {'id': str(uuid.uuid4()), 'ree': ree_base64, 'tee': tee_base64}
            completed_task = {'id': str(uuid.uuid4()), 'dateCreated': date_created, 'taskType': 'TRAINING', 'status': 'COMPLETED', 'supertask': {'id': supertask['id']}, 'outputModels': [local_model]}
            producer.send('client-done-tasks', completed_task).add_callback(on_send_success).add_errback(on_send_error)

        # block until all async messages are sent
        producer.flush()

        logging.info("============= poll global model =============")

if __name__ == '__main__':
    main()
