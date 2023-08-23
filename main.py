#!/usr/bin/python3

from ast import arg
from re import I
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSController, RemoteController, CPULimitedHost
from mininet.link import TCLink

import numpy as np
import csv

import os
import sys
import subprocess
import time

import argparse
import logging

import emuNetwork
import emuKafka
import emuZk
import emuLoad
import emuLogs
import emuStreamProc
import emuDataStore
import configParser
import latency_throughput_logs

pID=0
popens = {}

# Kill all subprocesses
def killSubprocs(brokerPlace, zkPlace, prodDetailsList, streamProcDetailsList, consDetailsList):	
	os.system("sudo pkill -9 -f bandwidth-monitor.py")
	os.system("sudo pkill -9 -f producer.py")
	os.system("sudo pkill -9 -f consumer.py")

	# killing producer processes
	for prod in prodDetailsList:
		producerScript = prod["producerPath"]
		prodKillStatus = os.system("sudo pkill -9 -f "+producerScript)
	
	# killing spark processes
	for spe in streamProcDetailsList:
		speScript = spe["applicationPath"]
		speKillStatus = os.system("sudo pkill -9 -f "+speScript)

	# killing consumer processes
	for cons in consDetailsList:
		consScript = cons["consumerPath"]
		consKillStatus = os.system("sudo pkill -9 -f "+consScript)

	for bk in brokerPlace:
		bID = bk["nodeId"]
		os.system("sudo pkill -9 -f server"+str(bID)+".properties") 

	os.system("sudo pkill -9 -f zookeeper") 

	# killing the topic duplicate python script
	os.system("sudo pkill -9 -f topicDuplicate.py") 

if __name__ == '__main__': 
	parser = argparse.ArgumentParser(description='Emulate data sync in mission critical networks.')
	parser.add_argument('topo', type=str, help='Network topology')
	parser.add_argument('--time', dest='duration', type=int, default=10, help='Duration of the simulation (in seconds)')
	parser.add_argument('--capture-all', dest='captureAll', action='store_true', help='Capture the traffic of all the hosts')
	parser.add_argument('--only-spark', dest='onlySpark', type=int, default=0, help='To run Spark application only')
	  
	args = parser.parse_args()
	# print(args)
 
	field_names = ['compression', 'batchSize', 'linger','n_topics','fetch_time','Throughput', 'Latency']
	filename = 'data.csv'
	with open(filename, 'a', newline='') as file:
		writer = csv.DictWriter(file, fieldnames=field_names)
		
		if file.tell() == 0:
			writer.writeheader()

		#Clean up mininet state
		for i in range(1000):
			
			cleanProcess = subprocess.Popen("sudo mn -c", shell=True)
			time.sleep(2)

			#Instantiate network
			emulatedTopo = emuNetwork.CustomTopo(args.topo)

			net = Mininet(topo = None,
					controller=RemoteController,
					link = TCLink,
					autoSetMacs = True,
					autoStaticArp = True,
					build=False,
					host= CPULimitedHost)  # support for CPU limited host

			net.topo = emulatedTopo
			net.build()

			brokerPlace, zkPlace, topicPlace, prodDetailsList, consDetailsList, isDisconnect, \
				dcDuration, dcLinks, switchPlace, hostPlace, streamProcDetailsList = configParser.readConfigParams(net, args)

			data = {}
			print(prodDetailsList)
			for j in prodDetailsList:
					if j['nodeId'] == '1':
						data['compression'] = j['compression']
						data['batchSize'] = j['batchSize']
						data['linger'] = j['linger']
						data['n_topics'] = len(topicPlace)
						data['fetch_time'] = brokerPlace[0]['replicaMaxWait']
						break
			nTopics = len(topicPlace)
			nSwitches = len(switchPlace)
			nHosts = len(hostPlace)
			print("Number of switches in the topology: "+str(nSwitches))
			print("Number of hostnodes in the topology: "+str(nHosts))
			print("Number of zookeepers in the topology: "+str(len(zkPlace)))
			print("Number of brokers in the topology: "+str(len(brokerPlace)))
			print("Number of topics: "+str(nTopics))
			
			# checking whether the application is only kafka or kafka-spark
			storePath = emuStreamProc.getStreamProcDetails(net, args.topo)
			if not streamProcDetailsList:   # if there is no configuration for spark
				args.onlyKafka = 1
			else:
				args.onlyKafka = 0
				#Add dependency to connect kafka & Spark
				emuStreamProc.addStreamProcDependency()

			killSubprocs(brokerPlace, zkPlace, prodDetailsList, streamProcDetailsList, consDetailsList)
			
			emuLogs.cleanLogs()
			emuDataStore.cleanDataStoreState()
			emuKafka.cleanKafkaState(brokerPlace)
			emuZk.cleanZkState(zkPlace)
				
			if storePath != "":
				print("Data store path: "+storePath)
				emuDataStore.configureKafkaDataStoreConnection(brokerPlace)
				# Add NAT connectivity
				net.addNAT().configDefault()  

			logDir = emuLogs.configureLogDir(nSwitches, nTopics, args.captureAll)
			emuZk.configureZkCluster(zkPlace)
			emuKafka.configureKafkaCluster(brokerPlace, zkPlace)

			#Start network
			net.start()
			for switch in net.switches:
				net.get(switch.name).start([])

			logging.info('Network started')

			#emuNetwork.configureNetwork(args.topo)
			time.sleep(1)

			print("Testing network connectivity")
			net.pingAll()
			print("Finished network connectivity test")
					
			#Start monitoring tasks
			popens[pID] = subprocess.Popen("sudo python3 bandwidth-monitor.py "+str(nSwitches)+" &", shell=True)
			pID += 1

			emuZk.runZk(net, zkPlace, logDir)
			if (emuKafka.runKafka(net, brokerPlace)) == False:
				killSubprocs(brokerPlace, zkPlace, prodDetailsList, streamProcDetailsList, consDetailsList)
				net.stop()
			
				emuLogs.cleanLogs()
				emuDataStore.cleanDataStoreState()
				emuKafka.cleanKafkaState(brokerPlace)
				emuZk.cleanZkState(zkPlace)
				emuStreamProc.cleanStreamProcDependency()
				continue
			
			emuLoad.runLoad(net, args, topicPlace, prodDetailsList, consDetailsList, streamProcDetailsList,\
				storePath, isDisconnect, dcDuration, dcLinks, logDir)

			# CLI(net)
			print("Simulation complete")

			# to kill all the running subprocesses
			killSubprocs(brokerPlace, zkPlace, prodDetailsList, streamProcDetailsList, consDetailsList)

			net.stop()
			logging.info('Network stopped')

			# Clean kafka-MySQL connection state before new simulation
			if storePath != "":
				emuDataStore.cleanDataStoreState()

			#Need to clean both kafka and zookeeper state before a new simulation
			emuKafka.cleanKafkaState(brokerPlace)
			emuZk.cleanZkState(zkPlace)

			#Need to clean spark dependency before a new simulation
			emuStreamProc.cleanStreamProcDependency()
	
			Thr = latency_throughput_logs.plotAggregatedBandwidth()
			Thr_avg = sum(Thr) / len(Thr)

			prodDetails = [{'prodNodeID':1, 'prodInstID':1},{'prodNodeID':2, 'prodInstID':1},
					{'prodNodeID':3, 'prodInstID':1},{'prodNodeID':4, 'prodInstID':1},{'prodNodeID':5, 'prodInstID':1},{'prodNodeID':6, 'prodInstID':1},
					{'prodNodeID':7, 'prodInstID':1},{'prodNodeID':8, 'prodInstID':1},{'prodNodeID':9, 'prodInstID':1},{'prodNodeID':10, 'prodInstID':1}]
			consDetails = [{'consNodeID':1, 'consInstID':1}, {'consNodeID':2, 'consInstID':1},{'consNodeID':3, 'consInstID':1},{'consNodeID':4, 'consInstID':1},
					{'consNodeID':5, 'consInstID':1},{'consNodeID':6, 'consInstID':1},{'consNodeID':7, 'consInstID':1},{'consNodeID':8, 'consInstID':1}
					,{'consNodeID':9, 'consInstID':1},{'consNodeID':10, 'consInstID':1}]
			nProducer = len(prodDetails)
			nConsumer = len(consDetails)
			logDir = 'logs/output/'
			nTopic = 1
			print(nProducer)
			switches = 10 #args.switches
				# logDir = args.logDir

			os.system("sudo rm "+logDir+"latency-log.txt"+"; sudo touch "+logDir+"latency-log.txt")  
			os.makedirs(logDir+"cons-latency-logs", exist_ok=True)

			

			latency_throughput_logs.initConsStruct(switches)
			latency_throughput_logs.readConsumerData(prodDetails, consDetails, nProducer, nConsumer, logDir)

				# for prodId in range(switches):
			for producer in prodDetails:
				latency_throughput_logs.getProdDetails(producer, logDir, nConsumer, consDetails)


			Late = latency_throughput_logs.plotLatencyScatter(logDir)
			late_avg = sum(Late)/len(Late)
		

				
			data['Throughput'] = Thr_avg
			data['Latency'] = late_avg
			writer.writerow(data)
			print(i,'-------------------------------------------------------------------------------------------')

  
