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
import configparser
 
def loadConfig():
    config = configparser.ConfigParser()
    if not config.read('config.ini'):
        config['fleet.user'] = {}
        config['fleet.user']['Username'] = ''
        config['fleet.user']['Password'] = ''
        config['fleet.device'] = {}
        config['fleet.device']['SecurityLevel'] = ''
        config['fleet.server'] = {}
        config['fleet.server']['Address'] = 'fleet.haoweihu.com'
        config['fleet.server']['Port'] = '8443'
        config['fleet.kafka'] = {}
        config['fleet.kafka']['Server'] = ''
        config['fleet.kafka']['Username'] = ''
        config['fleet.kafka']['Password'] = ''
        config['fleet.algorithm'] = {}
        config['fleet.algorithm']['MaxRetrains'] = '2'
        config['fleet.statistics'] = {}
        config['fleet.statistics']['TrainingCount'] = '0'
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
    return config

def saveConfig(config):
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

def setupLogger():
    formatter = logging.Formatter("%(asctime)s %(levelname)s (%(threadName)s) %(message)s")
    logger = logging.getLogger()
    logger.level = logging.INFO
    fileHandler = logging.FileHandler("fleet.log")
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

def getMacAddress():
    return ':'.join(re.findall('..', '%012x' % uuid.getnode()))

def user_register(username, password):
    params = urllib.parse.urlencode({'username': username, 'password': password})
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    conn = http.client.HTTPSConnection(config['fleet.server']['Address'], int(config['fleet.server']['Port']))
    conn.request("POST", "/api/public/register", params, headers)
    response = conn.getresponse()
    if response.status != 200:
        return None
    logging.info("%s %s" % (response.status, response.reason))
    data = response.read()
    conn.close()
    return json.loads(data.decode('ascii'))

def user_login(username, password):
    credentials = "Basic " + base64.b64encode((username + ":" + password).encode("ascii")).decode("ascii")
    headers = {"Authorization": credentials}
    conn = http.client.HTTPSConnection(config['fleet.server']['Address'], int(config['fleet.server']['Port']))
    conn.request("GET", "/api/users/login", headers=headers)
    response = conn.getresponse()
    logging.info("%s %s" % (response.status, response.reason))
    if response.status != 200:
        if response.status == 401:
            logging.error("The username or password is incorrect!")
        return None
    data = response.read()
    conn.close()
    return data.decode('ascii')

def run_diagnosis():
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

def setupKafka():
    servers = [config['fleet.kafka']['Server']]
    username = config['fleet.kafka']['Username']
    password = config['fleet.kafka']['Password']

    # consume earliest available messages, don't commit offsets
    consumer = KafkaConsumer('client-todo-tasks',
                             group_id='fleet-client' + '-' + getMacAddress(),
                             bootstrap_servers=servers, 
                             value_deserializer=lambda m: json.loads(m.decode('ascii')), 
                             auto_offset_reset='earliest', 
                             enable_auto_commit=True,
                             max_poll_interval_ms=43200000,
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
    return producer, consumer

def on_kafka_send_success(record_metadata):
    logging.info("%s:%d:%d" % (record_metadata.topic, record_metadata.partition,
                                      record_metadata.offset))

def on_kafka_send_error(excp):
    logging.error('Failed to send the local model!', exc_info=excp)
    # handle exception

def run_training_loop(producer, consumer, user_id):
    mac_address = getMacAddress()
    device_id = uuid.uuid3(uuid.UUID('00000000-0000-0000-0000-000000000000'), mac_address)

    max_retrains = int(config['fleet.algorithm']['MaxRetrains'])
    retrain = 0
    last_offset = -1
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
        config['fleet.statistics']['TrainingCount'] = str(config['fleet.statistics'].getint('TrainingCount') + 1)
        saveConfig(config)

        with open("/root/tmp/backup/mnist_lenet.weights_ree", "rb") as ree_file, open("/root/tmp/backup/mnist_lenet.weights_tee", "rb") as tee_file:
            ree_base64 = base64.b64encode(ree_file.read()).decode("ascii")
            tee_base64 = base64.b64encode(tee_file.read()).decode("ascii")
            local_model = {'id': str(uuid.uuid4()), 'ree': ree_base64, 'tee': tee_base64}
            user = {'id': user_id}
            device = {'id': str(device_id), 'macAddress': mac_address, 'securityLevel': int(config['fleet.device']['SecurityLevel'])}
            completed_task = {'id': str(uuid.uuid4()), 'user': user, 'device': device, 'dateCreated': date_created, 'taskType': 'TRAINING', 'status': 'COMPLETED', 'supertask': {'id': supertask['id']}, 'outputModels': [local_model]}
            producer.send('client-done-tasks', completed_task).add_callback(on_kafka_send_success).add_errback(on_kafka_send_error)

        # block until all async messages are sent
        producer.flush()

        logging.info("============= poll global model =============")
    
def main():
    setupLogger()
    if not config['fleet.device']['SecurityLevel']:
        config['fleet.device']['SecurityLevel'] = str(run_diagnosis())
        saveConfig(config)
    username = config['fleet.user']['username']
    password = config['fleet.user']['password']
    while True:
        if username:
            if not password:
                password = getpass.getpass()
            login_result = user_login(username, password)
            if login_result:
                break
            else:
                logging.info("Login failed.")
        username = input('Username: ')
        password = getpass.getpass()
    producer, consumer = setupKafka()
    run_training_loop(producer, consumer, login_result)
    
if __name__ == '__main__':
    config = loadConfig()
    main()
