
import yaml
from yaml.loader import SafeLoader

import sys
import networkx as nx
import numpy as np

GROUP_MIN_SESSION_TIMEOUT_MS = 6000
GROUP_MAX_SESSION_TIMEOUT_MS = 1800000
REPLICA_LAG_TIME_MAX_MS = 30000

def readYAMLConfig(configPath):
	data = []

	try:
		with open(configPath, 'r') as f:
			data = list(yaml.load_all(f, Loader=SafeLoader))
			print(data)
	except yaml.YAMLError:
		print("Error in configuration file")

	return data


def validateBrokerParameters(brokerConfig, nodeID, replicaMaxWait, replicaMinBytes):
	# This value should always be less than the replica.lag.time.max.ms at all times to prevent frequent shrinking of ISR for low throughput topics
	print(replicaMaxWait)
	if replicaMaxWait >= REPLICA_LAG_TIME_MAX_MS:
		print("ERROR in producer at node "+str(nodeID)+": replica.fetch.wait.max.ms must be less than the replica.lag.time.max.ms value of " +  str(REPLICA_LAG_TIME_MAX_MS) + " at all times.")
		sys.exit(1)
	
def readBrokerConfig(brokerConfigPath, nodeID, replicaMaxWait):
	brokerConfig = readYAMLConfig(brokerConfigPath)

	# Apache Kafka broker parameters
	if len(brokerConfig) == 0:
		replicaMaxWait = 500
		replicaMinBytes = 1
	else:
		
		# replicaMaxWait = 500 if brokerConfig[0].get("replicaMaxWait", 500) is None else brokerConfig[0].get("replicaMaxWait", 500)
		replicaMinBytes = 1 if brokerConfig[0].get("replicaMinBytes", 1) is None else brokerConfig[0].get("replicaMinBytes", 1)

	validateBrokerParameters(brokerConfig, nodeID, replicaMaxWait, replicaMinBytes)

	brokerDetails = {"nodeId": nodeID, "replicaMaxWait": replicaMaxWait, 'replicaMinBytes': replicaMinBytes}
	print("Broker details at node "+str(nodeID)+":")
	print(brokerDetails)

	return brokerDetails 

# reading from producer YAML specification
def readProdConfig(prodConfigPath, producerType, nodeID, prodDetails):
	prodConfig = readYAMLConfig(prodConfigPath)

	prodFile = "None" if prodConfig[0].get("filePath", "None") is None else prodConfig[0].get("filePath", "None")
	prodTopic = "None" if prodConfig[0].get("topicName", "None") is None else prodConfig[0].get("topicName", "None")
	prodNumberOfFiles = "0" if str(prodConfig[0].get("totalMessages", "0")) is None else str(prodConfig[0].get("totalMessages", "0"))
	nProducerInstances = "1" if str(prodConfig[0].get("producerInstances", "1")) is None else str(prodConfig[0].get("producerInstances", "1"))
	producerPath = "producer.py" if prodConfig[0].get("producerPath", "producer.py") is None else prodConfig[0].get("producerPath", "producer.py")


	acks = prodDetails[0]
	compression = prodDetails[1]
	batchSize = prodDetails[2]
	linger = prodDetails[3]
	# Apache Kafka parameters
	# acks = 1 if prodConfig[0].get("acks", 1) is None else prodConfig[0].get("acks", 1)
	# compression = "None" if str(prodConfig[0].get("compression", "None")) is None else str(prodConfig[0].get("compression", "None"))
	# batchSize = 16384 if prodConfig[0].get("batchSize", 16384) is None else prodConfig[0].get("batchSize", 16384)
	# linger = 0 if prodConfig[0].get("linger", 0) is None else prodConfig[0].get("linger", 0)
	requestTimeout = 30000 if prodConfig[0].get("requestTimeout", 30000) is None else prodConfig[0].get("requestTimeout", 30000)
	bufferMemory = 33554432 if prodConfig[0].get("bufferMemory", 33554432) is None else prodConfig[0].get("bufferMemory", 33554432)

	# S2G producer parameters
	mRate = "None" if str(prodConfig[0].get("messageRate", "None")) is None else str(prodConfig[0].get("messageRate", "None"))

	validateProducerParameters(prodConfig, nodeID, producerType, acks, compression, mRate)

	prodDetails = {"nodeId": nodeID, "producerType": producerType,\
					"produceFromFile":prodFile, "produceInTopic": prodTopic,\
					"prodNumberOfFiles": prodNumberOfFiles, "nProducerInstances": nProducerInstances, \
					"producerPath": producerPath,\
					"acks":acks, "compression":compression, "batchSize": batchSize, \
					"linger": linger, "requestTimeout": requestTimeout, "bufferMemory": bufferMemory, \
					"mRate": mRate}
	
	# print("Producer details at node "+str(nodeID)+":")
	# print(prodDetails)

	return prodDetails 

# reading from consumer YAML specification
def readConsConfig(consConfigPath, consumerType, nodeID):
	consConfig = readYAMLConfig(consConfigPath)
	consTopic = "" if consConfig[0].get("topicName", "") is None else consConfig[0].get("topicName", "")
	nConsumerInstances = "1" if str(consConfig[0].get("consumerInstances", "1")) is None else str(consConfig[0].get("consumerInstances", "1"))
	consumerPath = "consumer.py" if consConfig[0].get("consumerPath", "consumer.py") is None else consConfig[0].get("consumerPath", "consumer.py")
	fetchMinBytes = 1 if int(consConfig[0].get("fetchMinBytes", 1)) is None else int(consConfig[0].get("fetchMinBytes", 1))
	fetchMaxWait = 500 if int(consConfig[0].get("fetchMaxWait", 500)) is None else int(consConfig[0].get("fetchMaxWait", 500))
	sessionTimeout = 10000 if int(consConfig[0].get("sessionTimeout", 10000)) is None else int(consConfig[0].get("sessionTimeout", 10000))

	# Note that the value must be in the allowable range as configured in the broker configuration by group.min.session.timeout.ms and group.max.session.timeout.ms
	if sessionTimeout < GROUP_MIN_SESSION_TIMEOUT_MS or sessionTimeout > GROUP_MAX_SESSION_TIMEOUT_MS:
		print("ERROR: Session timeout must be in the allowable range as configured in the broker configuration by group.min.session.timeout.ms value of " + str(GROUP_MIN_SESSION_TIMEOUT_MS) + " and group.max.session.timeout.ms value of " + str(GROUP_MAX_SESSION_TIMEOUT_MS))
		sys.exit(1)

	if consumerType == 'CUSTOM' and consumerPath == "consumer.py":
		print("ERROR: for CUSTOM consumer, consumer file path is required")
		sys.exit(1)
	elif consumerType == 'STANDARD' and consTopic == "" :
		print("ERROR: for STANDARD consumer, topic name is required")	
		sys.exit(1)
	
	consDetails = {"nodeId": nodeID, "consumerType": consumerType,\
					"consumeFromTopic": consTopic, "nConsumerInstances": nConsumerInstances, \
					"consumerPath": consumerPath, "fetchMinBytes": fetchMinBytes, \
					"fetchMaxWait": fetchMaxWait, "sessionTimeout": sessionTimeout}

	return consDetails 

def readFaultConfig(faultConfigPath):
	faultyLinks  = []
	faultConfig = readYAMLConfig(faultConfigPath)
	faultDuration = 60 if int(faultConfig[0].get("duration", 60)) is None else int(faultConfig[0].get("duration", 60))
	links = "" if faultConfig[0].get("links", "") is None else faultConfig[0].get("links", "")
	faultyLinks = links.split(',')

	print("read fault config:")
	print(faultDuration)
	print(*faultyLinks)
	return faultDuration, faultyLinks


def validateProducerParameters(prodConfig, nodeID, producerType, acks, compression, mRate):
	if producerType == 'CUSTOM' and len(prodConfig[0]) != 2:
		print("ERROR: required parameters for CUSTOM producer at producer on node "+str(nodeID)+": producer file path and number of producer instance")
		sys.exit(1)
	if producerType == 'STANDARD' and len(prodConfig[0]) < 2:
		print("ERROR: required parameters for STANDARD producer at producer on node "+str(nodeID)+": name of the topic to produce and number of producer instances")
		sys.exit(1)
	if producerType != 'CUSTOM' and producerType != 'STANDARD' and len(prodConfig[0]) < 4:
		print("ERROR: required parameters for "+str(producerType)+" producer at producer on node "+str(nodeID)+": file to produce, name of the topic to produce, number of files and number of producer instances")
		sys.exit(1)

	if acks < 0 or acks >= 3:
		print("ERROR: acks value should be 0, 1 or 2 (which represents all) in producer at node "+str(nodeID))
		sys.exit(1)

	compressionList = ['gzip', 'snappy', 'lz4']
	if not (compression in compressionList) and compression != 'None':
		print("ERROR: at producer on node "+str(nodeID)+" compression should be None or one of the following:")
		print(*compressionList, sep = ", ") 
		sys.exit(1)
	if mRate != "None" and float(mRate) > 100:
		print("ERROR: Message rate on producer at node "+str(nodeID)+" should be less than 100 msg/second.")
		sys.exit(1)

def readStreamProcConfig(streamProcConfigPath, nodeID):
	streamProcConfig = readYAMLConfig(streamProcConfigPath)
	speApp = "" if streamProcConfig[0].get("app", "") is None else streamProcConfig[0].get("app", "")
	if speApp == "" or speApp == None:
		print('ERROR: stream processing application path not specified correctly in node '+str(nodeID))
	
	return speApp

def readConfigParams(net, args):
	inputTopoFile = args.topo
	onlySpark =  args.onlySpark

	brokerPlace = []
	zkPlace = []
	switchPlace = []
	hostPlace = []

	topicPlace = []

	prodDetailsList = []
	consDetailsList = []
	streamProcDetailsList = []

	#Read topo information
	try:
		inputTopo = nx.read_graphml(inputTopoFile)
	except Exception as e:
		print("ERROR: Could not read topo properly.")
		print(str(e))
		sys.exit(1)
  

	#Read topic information
	if onlySpark == 0: 
		topicConfigPath = inputTopo.graph["topicConfig"]
		print("topic config directory: " + topicConfigPath)
		topicPlace = readYAMLConfig(topicConfigPath)
		n_copy_list = [2, 6, 10]
		n_copy = np.random.randint(1,10)
		print(n_copy)
		topicPlace = [topicPlace[0].copy() for _ in range(n_copy)]
		for i in range(len(topicPlace)):
			topicPlace[i]['topicName'] = 'topic-'+str(i)
			topicPlace[i]['topicBroker'] = (i+1)
		print(topicPlace)

	# reading fault config
	try:
		dcPath = inputTopo.graph["faultConfig"]
		isDisconnect = 1
		print("Fault config directory: " + dcPath)
		dcDuration, dcLinks = readFaultConfig(dcPath)
	except KeyError:
		print("No fault is set")
		isDisconnect = 0
		dcDuration = 0
		dcLinks = []

	#Read nodewise switch, host, broker, zookeeper, producer, consumer information
	nSwitches = 0
	nHosts = 0
	try:
		prodParams = []
		acks = 1
		prodParams.append(acks)
		compression = np.random.choice(['None','gzip','snappy'],replace=False)
		prodParams.append(compression)
		batchSizeList = [4096, 134121, 262145]
		batchSize = np.random.randint(4096,262146)
		prodParams.append(batchSize)
		lingerList = [0, 50, 100]
		linger = np.random.randint(0,101)
		prodParams.append(linger)
		replicaMaxWaitList = [1, 10000, 29000]
		replicaMaxWait = np.random.randint(1,30000)
		for node, data in inputTopo.nodes(data=True):  
			if node[0] == 'h':
				nodeID = node[1:]
				nHosts += 1 
				hostPlace.append(node[1:]) 
				if 'zookeeper' in data: 
					if data["zookeeper"] == 1:
						zkPlace.append(node[1:]) 
					elif data["zookeeper"] == 0:
						pass
					else:
						print("ERROR: zookeeper attribute only supports boolean input. Please check zookeeper attribute seting in node "+str(node))
						sys.exit(1)
				if 'brokerConfig' in data: 
					brokerDetails = readBrokerConfig(data["brokerConfig"], nodeID, replicaMaxWait)
					brokerPlace.append(brokerDetails)
				if 'producerType' in data: 
					producerType = data["producerType"]
					prodDetails = readProdConfig(data["producerConfig"], producerType, nodeID, prodParams)
					prodDetailsList.append(prodDetails)
				if 'consumerType' in data:
					consumerType = data["consumerType"]
					consDetails = readConsConfig(data["consumerConfig"], consumerType, nodeID)
					consDetailsList.append(consDetails)
				if 'streamProcConfig' in data: 
					streamProcType = ""
					if 'streamProcType' in data: 
						streamProcType = data['streamProcType']
					streamProcApp = readStreamProcConfig(data["streamProcConfig"], nodeID)
					streamProcDetails = {"nodeId": nodeID, 'streamProcType': streamProcType, \
										"applicationPath": streamProcApp}
					streamProcDetailsList.append(streamProcDetails)
			elif node[0] == 's':
				nSwitches += 1
				switchPlace.append(node[1:]) 
	except KeyError as e:
		print("Node attributes are not set properly: "+str(e))
		sys.exit(1)

	print("zookeepers:")
	print(*zkPlace)
	# print("brokers: \n")
	# print(*brokerPlace)

	# print("producer details: ")
	# print(*prodDetailsList)

	# print("consumer details: ")
	# print(*consDetailsList)

	return brokerPlace, zkPlace, topicPlace, prodDetailsList, consDetailsList, \
		isDisconnect, dcDuration, dcLinks, switchPlace, hostPlace, streamProcDetailsList