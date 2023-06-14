#!/usr/bin/python3

from kafka import KafkaConsumer

from random import seed, random

import sys
import time

import logging

try:
	seed(2)
	nodeName = sys.argv[1]
	consInstance = sys.argv[2]
	brokerId = sys.argv[3]
	nodeID = nodeName[1:]
	

	nTopics = 1      
	cRate = 0.5
	fetchMinBytes = 1
	fetchMaxWait = 500
	sessionTimeout = 10000 
	topicCheckInterval = 0.1

	logDir = "logs/output"
	logging.basicConfig(filename=logDir+"/cons/"+"cons-node"+nodeID+\
		"-instance"+str(consInstance)+".log",\
		format='%(asctime)s %(levelname)s:%(message)s',\
		level=logging.INFO)
	logging.info("Individual consumer single")
	logging.info("node to initiate consumer: "+nodeID)

	consumers = []
	timeout = int((1.0/cRate) * 1000)
	bootstrapServers="10.0.0."+str(brokerId)+":9092"  

	# One consumer for all topics
	topicName = 'topic-0'
	logging.info("topicName "+topicName)
	consumptionLag = random() < 0.95				
	logging.info("**Configuring KafkaConsumer** topicName=" + topicName + " bootstrap_servers=" + str(bootstrapServers) +
		" consumer_timeout_ms=" + str(timeout) + " fetch_min_bytes=" + str(fetchMinBytes) +
		" fetch_max_wait_ms=" + str(fetchMaxWait) + " session_timeout_ms=" + str(sessionTimeout))

	consumer = KafkaConsumer(
		bootstrap_servers=bootstrapServers,
		auto_offset_reset='latest' if consumptionLag else 'earliest',
		enable_auto_commit=True,
		consumer_timeout_ms=timeout,
		fetch_min_bytes=fetchMinBytes,
		fetch_max_wait_ms=fetchMaxWait,
		session_timeout_ms=sessionTimeout,
		# group_id="group-"+str(nodeID)+"-instance"+str(consInstance)                                     
	)	
	consumer.subscribe(pattern=topicName)

	# Poll the data
	logging.info('Connect to broker looking for topic %s. Timeout: %s.', topicName, str(timeout))
	messages = {}
	while True:
		startTime = time.time()		
		logging.info(consumer)
		for msg in consumer:
			logging.info(msg)
			try:
				msgContent = str(msg.value, 'utf-8')
				prodID = msgContent[:2]
				msgID = msgContent[2:8]
				topic = msg.topic
				offset = str(msg.offset)    

				key = prodID+"-"+msgID+"-"+topic
				if key in messages:
					logging.warn('ProdID %s MSG %s Topic %s already read. Not logging.', prodID, msgID, topic)				         
				else:
					messages[key] = offset
					logging.info('Prod ID: %s; Message ID: %s; Latest: %s; Topic: %s; Offset: %s; Size: %s', prodID, msgID, str(consumptionLag), topic, offset, str(len(msgContent)))           			
			except Exception as e:
				logging.error(e + " from messageID %s", msgID)				
		stopTime = time.time()
		topicCheckWait = topicCheckInterval -(stopTime - startTime)
		if(topicCheckWait > 0):
			logging.info('Sleeping for topicCheckWait: %s', str(topicCheckWait))
			time.sleep(topicCheckWait)

except Exception as e:
	logging.error(e)	
finally:
	consumer.close()
	logging.info('Disconnect from broker')
	sys.exit(1)