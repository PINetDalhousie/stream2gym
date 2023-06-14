#!/usr/bin/python3

from mininet.net import Mininet

import os
import sys
import subprocess
import time
import networkx as nx

def configureKafkaCluster(brokerPlace, zkPlace):
	print("Configure kafka cluster")

	propertyFile = open("kafka/config/server.properties", "r")
	serverProperties = propertyFile.read()

	for bk in brokerPlace:
		bID = bk["nodeId"]
		replicaMaxWait = bk["replicaMaxWait"]
		replicaMinBytes = bk["replicaMinBytes"]
		os.system("sudo mkdir kafka/kafka" + str(bID) + "/")

		bProperties = serverProperties
		bProperties = bProperties.replace("broker.id=0", "broker.id="+str(bID))
		bProperties = bProperties.replace(
			"#advertised.listeners=PLAINTEXT://your.host.name:9092", 
			"advertised.listeners=PLAINTEXT://10.0.0." + str(bID) + ":9092")
		bProperties = bProperties.replace("log.dirs=/tmp/kafka-logs",
			"log.dirs=./kafka/kafka" + str(bID))

		bProperties = bProperties.replace("#replica.fetch.wait.max.ms=500", "replica.fetch.wait.max.ms="+str(replicaMaxWait))
		bProperties = bProperties.replace("#replica.fetch.min.bytes=1", "replica.fetch.min.bytes="+str(replicaMinBytes))

		bProperties = bProperties.replace(
            "offsets.topic.replication.factor=1", "offsets.topic.replication.factor=2")

		#Specify zookeeper addresses to connect
		zkAddresses = ""
		zkPort = 2181

		for i in range(len(zkPlace)-1):
			zkAddresses += "10.0.0." + str(zkPlace[i]) + ":" +str(zkPort)+","
			# zkAddresses += "localhost:"+str(zkPort)+","
			zkPort += 1

		# zkAddresses += "localhost:"+str(zkPort)
		zkAddresses += "10.0.0."+str(zkPlace[-1])+ ":" +str(zkPort)
		print("zk connect: " + zkAddresses)

		bProperties = bProperties.replace(
			"zookeeper.connect=localhost:2181",
			"zookeeper.connect="+zkAddresses)

		#bProperties = bProperties.replace(
		#	"zookeeper.connection.timeout.ms=18000",
		#	"zookeeper.connection.timeout.ms=30000")

		bFile = open("kafka/config/server" + str(bID) + ".properties", "w")
		bFile.write(bProperties)
		bFile.close()

	propertyFile.close()

def runKafka(net, brokerPlace, brokerWaitTime=200):

	netNodes = {}

	for node in net.hosts:
		print(node)
		netNodes[node.name] = node
		
	startTime = time.time()
	popens = {}
	for bk in brokerPlace:
		print(bk)
		bNode = bk["nodeId"]
		bID = "h"+str(bNode)

		startingHost = netNodes[bID]
		
		print("Creating Kafka broker at node "+str(bNode))

		# startingHost.popen("kafka/bin/kafka-server-start.sh kafka/config/server"+str(bNode)+".properties &", shell=True)
		popens[startingHost] = startingHost.popen(
            "kafka/bin/kafka-server-start.sh kafka/config/server"+str(bNode)+".properties &", shell=True)
		
		time.sleep(1)

	brokerWait = True
	totalTime = 0
	brokerCount = 0
	for bk in brokerPlace:
		bNode = bk["nodeId"]
		while brokerWait:
			print("Testing Connection to Broker " + str(bNode) + "...")
			out, err, exitCode = startingHost.pexec(
				"nc -z -v 10.0.0." + str(bNode) + " 9092")
			stopTime = time.time()
			totalTime = stopTime - startTime
			if(exitCode == 0):
				brokerWait = False
				brokerCount += 1
			# elif(totalTime > brokerWaitTime):
			#    print("ERROR: Timed out waiting for Kafka brokers to start")
			#    sys.exit(1)
			else:
				print("Waiting for Broker " + str(bNode) + " to Start...")
				time.sleep(10)
		brokerWait = True
	print("Successfully Created "+str(brokerCount)+" Kafka Brokers in " + str(totalTime) + " seconds")

def cleanKafkaState(brokerPlace):
	for bk in brokerPlace:
		bID = bk["nodeId"]
		os.system("sudo rm -rf kafka/kafka" + str(bID) + "/")
		os.system("sudo rm -f kafka/config/server" + str(bID) + ".properties")