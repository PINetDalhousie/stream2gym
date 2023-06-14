#!/usr/bin/python3

from ast import arg
from re import I
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSController, RemoteController, CPULimitedHost
from mininet.link import TCLink

from datetime import datetime, timedelta

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


pID=0
popens = {}
consLogs = []

prodCount = 0
consCount = 0
extraLatencyMessage = 0


def plotLatencyScatter():
    lineXAxis = []
    latencyYAxis = []
    # global latencyYAxis
    with open(logDir+"/latency-log.txt", "r") as f:
        for lineNum, line in enumerate(f,1):         #to get the line number
            lineXAxis.append(lineNum)
            if "Latency of this message: " in line:
                firstSplit = line.split("Latency of this message: 0:")
                print(firstSplit)
                if len(firstSplit) == 2:
                 latencyYAxis.append(float(firstSplit[1][0:2])*60.0 + float(firstSplit[1][3:5]))
    return latencyYAxis
                

def getProdDetails(prod, logDir):
    global prodCount
    global consLogs

    latencyLog = open(logDir+"/latency-log.txt", "a")
    
    prodLog = logDir+'/prod/prod-node'+str(prod['prodNodeID'])+'-instance'+str(prod['prodInstID'])+'.log'
    prodId = prod['prodNodeID']
    
    with open(prodLog) as f:
        for line in f:
            if "Topic-name: topic-" in line:
#                 msgProdTime = line.split(",")[0]
                msgProdTime = line.split(" INFO:Topic-name:")[0]
                topicSplit = line.split("topic-")
                topicId = topicSplit[1].split(";")[0]
                msgIdSplit = line.split("Message ID: ")
                msgId = msgIdSplit[1].split(";")[0]
                
                #print("producer: "+str(prodId)+" time: "+msgProdTime+" topic: "+topicId+" message ID: "+msgId)
                prodCount+=1

                if prodId < 10:
                    formattedProdId = "0"+str(prodId)
                else:
                    formattedProdId = str(prodId)

                for consId in range(nConsumer):
                    #print(formattedProdId+"-"+msgId+"-topic-"+topicId)
                    if formattedProdId+"-"+msgId+"-topic-"+topicId in consLogs[consId].keys():
                        msgConsTime = consLogs[consId][formattedProdId+"-"+msgId+"-topic-"+topicId]
                        
                        prodTime = datetime.strptime(msgProdTime, "%Y-%m-%d %H:%M:%S,%f")
                        consTime = datetime.strptime(msgConsTime, "%Y-%m-%d %H:%M:%S,%f")
                        latencyMessage = consTime - prodTime

                        #print(latencyMessage)
                        latencyLog.write("Producer ID: "+str(prodId)+" Message ID: "+msgId+" Topic ID: "+topicId+" Consumer ID: "+str(consId+1)+" Production time: "+msgProdTime+" Consumtion time: "+str(msgConsTime)+" Latency of this message: "+str(latencyMessage))
                        latencyLog.write("\n")    #latencyLog.write("\r\n")

                        # Write to the consumer latency log
                        consLatencyLog = open(logDir+"/cons-latency-logs/latency-log-cons-"+\
                            str(consDetails[consId]['consNodeID'])+'-instance'+str(consDetails[consId]['consInstID']) + ".txt", "a")
                        # consLatencyLog = logDir+'prod-node'+str(prod['prodNodeID'])+'-instance'+str(prod['prodInstID'])+'.log'
                        consLatencyLog.write("Producer ID: "+str(prodId)+" Message ID: "+msgId+" Topic ID: "+topicId+" Consumer ID: "+str(consId)+" Production time: "+msgProdTime+" Consumtion time: "+str(msgConsTime)+" Latency of this message: "+str(latencyMessage))
                        consLatencyLog.write("\n")    #latencyLog.write("\r\n")
                        consLatencyLog.close()

                        #getConsDetails(consId+1, prodId, msgProdTime, topicId, msgId)

        print("Prod " + str(prodId) + ": " + str(datetime.now()))

    latencyLog.close()

def initConsStruct(switches):
    global consLogs

    for consId in range(switches):
        newDict = {}
        consLogs.append(newDict)


def readConsumerData(prodDetails, consDetails, nProducer, nConsumer, logDir):
    consId = 1
    #print("Start reading cons data: " + str(datetime.now()))
    for cons in consDetails:
        #print(logDir+'cons/cons-'+str(consId)+'.log')
        f = open(logDir+'cons/'+'cons-node'+str(cons['consNodeID'])\
				+'-instance'+str(cons['consInstID'])+'.log')
        
        for lineNum, line in enumerate(f,1):         #to get the line number
            #print(line)

            if "Prod ID: " in line:
                lineParts = line.split(" ")
                #print(lineParts)

                prodID = lineParts[4][0:-1]
                #print(prodID)

                msgID = lineParts[7][0:-1]
                #print(msgID)

                topic = lineParts[11][0:-1]
                #print(topic)

                #print(prodID+"-"+msgID+"-"+topic)
                consLogs[consId-1][prodID+"-"+msgID+"-"+topic] = lineParts[0] + " " + lineParts[1]

        f.close()
        consId += 1

def readThroughput(switch,portNumber, portFlag):
    count=0
    dataList = []
    bandwidth =  [0]
    txFlag = 0
    maxBandwidth = -1.0
    
    with open('logs/output/bandwidth/'+'bandwidth-log'+str(switch)+'.txt') as f:
        
        for line in f:
            if portNumber >= 10:
                spaces = " "
            else:
                spaces = "  "
            if "port"+spaces+str(portNumber)+":" in line: 
                
                if portFlag == 'tx pkts':
                    line = f.readline()
                    
                elif portFlag == 'tx bytes':
                    line = f.readline()
                    txFlag = 1           
                if txFlag == 1:
                    newPortFlag = "bytes"
                    data = line.split(newPortFlag+"=")
                else:
                    data = line.split(portFlag+"=")

                data = data[1].split(",")
                dataList.append(int(data[0]))
                if count>0: 
                    individualBandwidth = (dataList[count]-dataList[count-1])/5
                    bandwidth.append(individualBandwidth)
                    if individualBandwidth > maxBandwidth:
                        maxBandwidth = individualBandwidth
                count+=1

    return bandwidth,count, maxBandwidth
    
    
def getAllThroughput():
    portParams = [(1,1)]
    
    allBandwidth = []
    countX = 0
    for ports in portParams:
        portId, switchId = ports
        bandwidth, occurrence, maxBandwidth = readThroughput(switchId,portId, 'rx pkts') 
        
        if countX == 0:
            countX = occurrence
        
        if len(bandwidth)<countX:
            for k in range(countX-len(bandwidth)):
                bandwidth.append(0)                    #filling with 0's to match up the length
            
        allBandwidth.append(bandwidth)

    bandwidthSum = []
    for i in range(countX):
        valWithLeader = 0
#         valWithoutLeader = 0
        for j in range(1):
            valWithLeader = valWithLeader+allBandwidth[j][i]
#             if (j+1) not in leaderReplicaList:         #to skip the leader replica curves
#                 valWithoutLeader = valWithoutLeader+allBandwidth[j][i]
        
        bandwidthSum.append(valWithLeader)
    return bandwidthSum
#         bandwidthSumLeaderLess.append(valWithoutLeader)

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
	field_names = ['acks', 'compression', 'batchSize', 'linger', 'requestTimeout', 'bufferMemory','Throughput', 'Latency']
	filename = 'data.csv'
	with open(filename, 'a', newline='') as file:
		writer = csv.DictWriter(file, fieldnames=field_names)
		
		if file.tell() == 0:
			writer.writeheader()
    
 

		#Clean up mininet state
		for i in range(100):
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

			print("Simulation complete")
			data = {}
			for j in prodDetailsList:
				if j['nodeId'] == '1':
					data['acks'] = j['acks']
					data['compression'] = j['compression']
					data['batchSize'] = j['batchSize']
					data['linger'] = j['linger']
					data['requestTimeout'] = j['requestTimeout']
					data['bufferMemory'] = j['bufferMemory']
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
			print(logDir)
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
			emuKafka.runKafka(net, brokerPlace)
			
			emuLoad.runLoad(net, args, topicPlace, prodDetailsList, consDetailsList, streamProcDetailsList,\
				storePath, isDisconnect, dcDuration, dcLinks, logDir)

			# CLI(net)
			

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
			Thr = getAllThroughput()
			Thr_avg = sum(Thr) / len(Thr)
			prodDetails = [{'prodNodeID':1, 'prodInstID':1}]
			consDetails = [{'consNodeID':3, 'consInstID':1}]
			nProducer = len(prodDetails)
			nConsumer = len(consDetails)
			logDir = 'logs/output/'
			nTopic = 1
			print(nProducer)
			switches = 1 #args.switches
			# logDir = args.logDir

			os.system("sudo rm "+logDir+"latency-log.txt"+"; sudo touch "+logDir+"latency-log.txt")  
			os.makedirs(logDir+"cons-latency-logs", exist_ok=True)

			print(datetime.now())

			initConsStruct(switches)
			readConsumerData(prodDetails, consDetails, nProducer, nConsumer, logDir)

			# for prodId in range(switches):
			for producer in prodDetails:
				getProdDetails(producer, logDir)


			Late = plotLatencyScatter()
			late_avg = sum(Late)/len(Late)
	

			
			data['Throughput'] = Thr_avg
			data['Latency'] = late_avg
			writer.writerow(data)
			print(i,'-------------------------------------------------------------------------------------------')
			break
 
     


  
