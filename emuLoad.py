#!/usr/bin/python3randint

from mininet.net import Mininet
from mininet.cli import CLI

from random import seed, randint, choice

import time
import os
import sys
import itertools
import logging

import subprocess
from subprocess import Popen, PIPE, STDOUT
from datetime import datetime

from emuLogs import ZOOKEEPER_LOG_FILE

# Method to extract Zookeeper leader information from Zookeeper log
def readCurrentZkLeader(logDir):
	zkLeader = None
	with open(logDir+"/" + ZOOKEEPER_LOG_FILE) as f:
		for line in f:
			if "LEADING - LEADER ELECTION TOOK " in line:
				first = line.split(">")[0]
				zkLeader = first[1:]
				# print(f'Zookeeper leader is {zkLeader}')
				break
	return zkLeader

# Method for logging topic(s) leader
def logTopicLeaders(net, logDir, topicPlace):
	# issuingNode = net.hosts[0]
	print("Finding topic leaders at localhost:2181")
	zkLeaderNode = readCurrentZkLeader(logDir)
	print("ZK Leader node is " + str(zkLeaderNode))
	logging.info("ZK Leader node is " + str(zkLeaderNode))
	for topic in topicPlace:
		topicName = topic["topicName"]
		issuingID = int(topic["topicBroker"])
		brokerId = int(topic["brokerId"][1:])
		issuingNode = net.hosts[issuingID-1]
		out = issuingNode.cmd("kafka/bin/kafka-topics.sh --bootstrap-server 10.0.0."+str(issuingID)+":9092 --describe --topic "+str(topicName), shell=True)
		# issuingNode = net.hosts[issuingID]
		# out = issuingNode.cmd("kafka/bin/kafka-topics.sh --bootstrap-server 10.0.0."+str(brokerId)+":9092 --describe --topic "+str(topicName), shell=True)
		split1 = out.split('Leader: ')
		print(split1)
		split2 = split1[1].split('\t')
		topicLeaderNode = 'h' + split2[0]			
		print(f"Leader for topic {str(topicName)} is node {topicLeaderNode}")
		logging.info(str(topicName) +" leader is node " + topicLeaderNode)

# Method to log the wireshark traces
def traceWireshark(hostsToCapture, f, logDir):
	for h in hostsToCapture:		
		#temp = h.nameToIntf		
		hostName = h.name
		filename = logDir + "/pcapTraces/" + hostName + "-eth1" + "-" + f + ".pcap"
		output = h.cmd("sudo tcpdump -i " + hostName +"-eth1 -w "+ filename +" &", shell=True)	
		print(output)

def spawnProducers(net, nTopics, args, prodDetailsList, topicPlace):
	# tClasses = tClassString.split(',')
	#print("Traffic classes: " + str(tClasses))

	# nodeClassification = {}
	netNodes = {}    
	
	#Distribute nodes among classes
	for node in net.hosts:
		netNodes[node.name] = node
	
	for prod in prodDetailsList:
		nodeID = 'h' + prod['nodeId']
		
		producerType = prod["producerType"]
		producerPath = prod["producerPath"]
		messageFilePath = prod['produceFromFile']
		# tClasses = prod['tClasses']
		prodTopic = prod['produceInTopic']
		prodNumberOfFiles = prod['prodNumberOfFiles']
		nProducerInstances = prod['nProducerInstances']
  
		brokerId = int(prod['brokerId'])
		
		# Apache Kafka producer parameters
		acks = prod['acks']
		compression = prod['compression']
		batchSize = prod['batchSize']
		linger = prod['linger']
		requestTimeout = prod['requestTimeout']
		bufferMemory = prod['bufferMemory']

		# S2G producer parameters
		mRate = prod['mRate']

		node = netNodes[nodeID]
  

		try:
			if producerType != 'CUSTOM':
				topicName = [x for x in topicPlace if x['topicName'] == prodTopic][0]["topicName"]
				brokerId = [x for x in topicPlace if x['topicName'] == prodTopic][0]["topicBroker"] 
				print("Producing messages to topic "+topicName+" at broker "+str(brokerId))
			
			prodInstance = 1

			while prodInstance <= int(nProducerInstances):
				if producerType == 'CUSTOM':
					# node.popen("python3 "+ producerPath +" " +nodeID+" "+str(prodInstance)+" "+str(brokerId)+" &", shell=True)
					node.popen("python3 "+producerPath+" "+nodeID+" "+str(prodInstance)+" "+str(brokerId)+" "+str(mRate)\
						+" "+str(nTopics)+" "+str(compression)+" "+str(batchSize)+" "+str(linger)\
						+" "+str(bufferMemory)+" &", shell=True)
					
				else:		
					try:
						node.popen("python3 "+producerPath+" "+nodeID+" "+str(prodInstance)+" "+prodNumberOfFiles+" "+str(mRate)\
						+" "+str(nTopics)+" "+str(acks)+" "+str(compression)+" "+str(batchSize)+" "+str(linger)\
						+" "+str(requestTimeout)+" "+str(bufferMemory)+" "+str(brokerId)+" "+messageFilePath\
						+" "+topicName+" "+producerType+" &", shell=True)

					except Exception as e:
						print('Error: '+str(e))
				
				prodInstance += 1

		except IndexError:
			print("Error: Production topic name not matched with the already created topics")
			sys.exit(1)
			
def spawnConsumers(net, consDetailsList, topicPlace):

	netNodes = {}

	for node in net.hosts:
		netNodes[node.name] = node
        
	for cons in consDetailsList:
		consInstance = 1
		
		consNode = cons["nodeId"]
		topicName = cons["consumeFromTopic"]
		consumerType = cons["consumerType"]
		consumerPath = cons["consumerPath"]
		nConsumerInstances = cons['nConsumerInstances']
		fetchMinBytes = cons['fetchMinBytes']
		fetchMaxWait  = cons['fetchMaxWait']
		sessionTimeout = cons['sessionTimeout']

		consID = "h"+consNode      
		node = netNodes[consID]
		brokerId = int(cons['brokerId'])

		# print("consumer node: "+consNode)
		# print("topic: "+topicName)
		# print("Number of consumers for this topic: "+str(nConsumerInstances))

		try:
			print("Consumer type: "+consumerType)
			if consumerType != 'CUSTOM':
				topicName = [x for x in topicPlace if x['topicName'] == topicName][0]["topicName"]
				brokerId = [x for x in topicPlace if x['topicName'] == topicName][0]["topicBroker"] 
				print("Consuming messages from topic "+topicName+" at broker "+str(brokerId))

			while consInstance <= int(nConsumerInstances):
				if consumerType == 'CUSTOM':
					
					node.popen("python3 "+consumerPath+" "+str(node.name)+" "+str(consInstance)+" "+str(fetchMaxWait)+" "+str(brokerId)+" &", shell=True)
					
				else:
					topicName = [x for x in topicPlace if x['topicName'] == topicName][0]["topicName"]
					brokerId = [x for x in topicPlace if x['topicName'] == topicName][0]["topicBroker"] 

					node.popen("python3 "+consumerPath+" "+str(node.name)+" "+topicName+" "+str(brokerId)+" "+str(consInstance)\
						+" "+str(fetchMinBytes)+" "+str(fetchMaxWait)+" "+str(sessionTimeout)+" &", shell=True)
				
				consInstance += 1

		except IndexError:
			print("Error: Consume topic name not matched with the already created topics")
			sys.exit(1)

def spawnSPEClients(net, streamProcDetailsList):
	netNodes = {}

	for node in net.hosts:
		netNodes[node.name] = node

	for spe in streamProcDetailsList:
		time.sleep(30)
		
		speNode = spe["nodeId"]
		speApp = spe["applicationPath"]
		print("spe node: "+speNode)
		print("spe App: "+speApp)
		print("*************************")

		speID = "h"+speNode
		node = netNodes[speID]

		# node.popen("sudo spark/pyspark/bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.1 "+sparkApp\
		# 			+" "+str(node.name)+" "+sparkOutputTo+" &", shell=True)

		node.popen("sudo spark/pyspark/bin/spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.1 "+speApp\
					+" &", shell=True)


def spawnKafkaDataStoreConnector(net, prodDetailsList, storePath):
	netNodes = {}

	for node in net.hosts:
		netNodes[node.name] = node
	
	connNode = prodDetailsList[0]["nodeId"]
	connID = "h"+connNode      
	node = netNodes[connID]

	print("=========")
	print("connector starts on node: "+connID)
	
	node.popen("sudo kafka/bin/connect-standalone.sh kafka/config/connect-standalone-new.properties "+ storePath +" > logs/connectorOutput.txt &", shell=True)

def runLoad(net, args, topicPlace, prodDetailsList, consDetailsList, streamProcDetailsList, \
	storePath, isDisconnect, dcDuration, dcLinks, logDir):

	nTopics = len(topicPlace)
	duration = args.duration

	# give some time to warm up the brokers
	time.sleep(5)

	print("Start workload")
	if args.captureAll:
		print("Started capturing wireshark traces")
		traceWireshark(net.hosts, "start", logDir)

	seed(1)

	nHosts = len(net.hosts)
	print("Number of hosts: " + str(nHosts))
    
	#Creating topic(s) in respective broker
	topicNodes = []
	startTime = time.time()

	for topic in topicPlace:
		topicName = topic["topicName"]
		issuingID = int(topic["topicBroker"])
		print(topic)
		topicPartition = topic["topicPartition"]
		topicReplica = topic["topicReplica"]
		issuingNode = net.hosts[issuingID-1]
		# issuingNode = net.hosts[issuingID]
		brokerId = topic["brokerId"][1:]
		print(issuingNode)
		print(net.hosts)

		print("Creating topic "+topicName+" at broker "+str(issuingID)+" partition "+str(topicPartition))

		# out = issuingNode.cmd("kafka/bin/kafka-topics.sh --create --bootstrap-server 10.0.0."+str(issuingID)+
		# 	":9092 --replication-factor "+str(topicReplica)+" --partitions " + str(topicPartition) +
		# 	" --topic "+topicName, shell=True)
		out = issuingNode.cmd("kafka/bin/kafka-topics.sh --create --bootstrap-server 10.0.0."+str(issuingID)+
			":9092 --replication-factor "+str(topicReplica)+" --partitions " + str(topicPartition) +
			" --topic "+topicName, shell=True)
		
		print(out)
		topicNodes.append(issuingNode)

		# topicDetails = issuingNode.cmd("kafka/bin/kafka-topics.sh --describe --bootstrap-server 10.0.0."+str(issuingID)+":9092", shell=True)
		topicDetails = issuingNode.cmd("kafka/bin/kafka-topics.sh --describe --bootstrap-server 10.0.0."+str(issuingID)+":9092", shell=True)
		print("Topic description at the beginning of the simulation:")
		print(topicDetails)

	stopTime = time.time()
	totalTime = stopTime - startTime
	print("Successfully Created " + str(len(topicPlace)) + " Topics in " + str(totalTime) + " seconds")
	
	#starting Kafka-data store connector
	if storePath != "":
		spawnKafkaDataStoreConnector(net, prodDetailsList, storePath)
		print("Kafka-data-store connector instance created")

	if args.onlyKafka == 0:
		spawnSPEClients(net, streamProcDetailsList)
		time.sleep(30)
		print("SPE Clients created")

	spawnProducers(net, nTopics, args, prodDetailsList, topicPlace)
	# time.sleep(120)
	print("Producers created")
	
	spawnConsumers(net, consDetailsList, topicPlace)
	# time.sleep(10)
	print("Consumers created")

	# Log the topic leaders
	logTopicLeaders(net, logDir, topicPlace)	

	timer = 0

	# Set up disconnect
	if isDisconnect:
		isDisconnected = False
		disconnectTimer = dcDuration
		hostsToDisconnect = []

	print(f"Starting workload at {str(datetime.now())}")
	logging.info('Starting workload at ' + str(datetime.now()))
	
	while timer < duration:
		time.sleep(10)
		percentComplete = int((timer/duration)*100)
		print("Processing workload: "+str(percentComplete)+"%")

		if isDisconnect and percentComplete >= 10:
			if not isDisconnected:	
				for link in dcLinks:
					linkSplit = link.split('-')
					n1 = net.getNodeByName(linkSplit[0])
					n2 = net.getNodeByName(linkSplit[1])
					hostsToDisconnect.append(n2)
					disconnectLink(net, n1, n2)

				isDisconnected = True

			elif isDisconnected and disconnectTimer <= 0: 	
				for link in dcLinks:
					linkSplit = link.split('-')
					n1 = net.getNodeByName(linkSplit[0])
					n2 = net.getNodeByName(linkSplit[1])				
					reconnectLink(net, n1, n2)
					if args.captureAll:
						traceWireshark(hostsToDisconnect, "reconnect", logDir)

					# checking topic leader after reconnection
					topicDetails = topicNodes[0].cmd("kafka/bin/kafka-topics.sh --describe --bootstrap-server 10.0.0.1:9092", shell=True)
					print("Topic description just after reconnection")
					print(topicDetails)

					logging.info("Topic description just after reconnection")
					logging.info(topicDetails)

				isDisconnected = False
				isDisconnect = False
				
			if isDisconnected:
				disconnectTimer -= 10

		timer += 10

	logTopicLeaders(net, logDir, topicPlace)
	print(f"Workload finished at {str(datetime.now())}")	
	logging.info('Workload finished at ' + str(datetime.now()))

def disconnectLink(net, n1, n2):
	print(f"***********Setting link down from {n1.name} <-> {n2.name} at {str(datetime.now())}")
	logging.info(f"***********Setting link down from {n1.name} <-> {n2.name} at {str(datetime.now())}")
	net.configLinkStatus(n2.name, n1.name, "down")
	net.pingAll()

def reconnectLink(net, n1, n2):
	print(f"***********Setting link up from {n1.name} <-> {n2.name} at {str(datetime.now())}")
	logging.info(f"***********Setting link up from {n1.name} <-> {n2.name} at {str(datetime.now())}")
	net.configLinkStatus(n2.name, n1.name, "up")
	net.pingAll()