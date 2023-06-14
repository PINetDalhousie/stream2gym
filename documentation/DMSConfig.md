# Modifying stream2gym for integrating DDPG with stream2gym

A project for modifying, refactoring, adding features, and bug fixing.

## Table of Contents

- [Introduction](#introduction)
- [Modifications](#modifications)
- [Usage](#usage)
- [Contributing](#contributing)
- [Bug Reporting](#bug-reporting)
- [License](#license)

## Introduction

DMSConfig which is a configuration tuning tool for Distributed Messaging Systems, uses Deep Deterministic Policy
Gradient(DDPG) method in order to tune the Kafka configuration parameters. This projects uses the same approach
to tune configuration parameters of DMS to get a high throughput and low latency using stream2gym and DDPG

## Modifications

We want to create an offline-simulator of stream2gym to train the DDPG agent, since integrating DDPG directly
with stream2gym will be very expensive in terms of amount of it takes to start stream2gym, set the parameters,
send messages, and get corresponding responses. In order to do that I implemented a simple scenario in which
we have a central switch(s1) and three hosts(h1, h2, h3). h1 has 1 producer and a zookeeper, h2 has the broker
and the lead zookeeper, and h3 has the consumer and a zookeeper. Then, I will run the application 100 times and 
will set up the producer with parameters such as , linger_time, batch_size, buffer_memory, and compression. In
each simulation we set a different value for each of the above parameters, send the messages, and compute the
corresponding latency and throughput. I used the military-coordination application. In order to adopt the above
changes, there were several files that needed to be changed which are: 
- [main.py](#main.py)
- [configParser.py](#configParser.py)
- [input.graphml](#input.graphml)
- [consumerConfiguration.yaml](#consumerConfiguration.yaml)
- [producerConfiguration.yaml](#producerConfiguration.yaml)
- [topicConfiguration.yaml](#topicConfiguration.yaml)
- [emuLoad.py](#emuLoad.py)
- [military-consumerSingle.py](#military-consumerSingle.py)
- [military-data-producer.py](#military-data-producer.py)

### main.py

1. I added a ``` for loop ``` in the main.py to run the experiment for 100 times and collect
the desired output and save them in .csv file 
2. After all the simulations were finished, I used the following code to get the average
throughput for a single run: 

```python
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


#Need to clean spark dependency before a new simulation
emuStreamProc.cleanStreamProcDependency()
Thr = getAllThroughput()
Thr_avg = sum(Thr) / len(Thr)
```
3. In this stage I use the following code to get the average latency for a single run:
```python

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
                        consLatencyLog = open(logDir+"/cons-latency-logs/latency-log-cons-"+
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
        f = open(logDir+'cons/'+'cons-node'+str(cons['consNodeID'])
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

-----------------------------------------------------------
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
```
4. At the end I collect all these information and save that in a csv file


### configParser.py

1. The default case in consumer and producer config-reader function was that 
there is a local broker being set up in the same node as the producer and consumer
are being set. readProdConfig() and readConsConfig() have been changed so that user
can also set the broker on a different node if they want to. validateProducerParameters()
has also been changed so that we can add on additional parameter to deal with 
broker set-up.

### input.graphml

1. This file contains the topology we want to use. I modified this file
so that we can have this topology:
                            
                            S1
                          / | \
                         /  |  \
                        H1  H2  H3
                        |   |   |
                       Z1P1 Z2B1 Z3C1

### consumerConfiguration.yaml
1. This file contains the path to consumer initialization code, number of consumer instances,
and I added brokerId to account for brokers that are located in a different node

### producerConfiguration.yaml
1. This file contains the path to producer initialization code, number of producer instances,
   and I added brokerId to account for brokers that are located in a different node

### topicConfiguration.yaml
1. This file contains the information about the topics we want to set up. brokerId to account for brokers that are located in a different node

### emuLoad.py
1. I changed the runLoad() function so that we can set the bootstrap-server based on the
broker id defined in the .yaml files
```python
for topic in topicPlace:
		topicName = topic["topicName"]
		issuingID = int(topic["topicBroker"])
		print(topic)
		topicPartition = topic["topicPartition"]
		topicReplica = topic["topicReplica"]
		# issuingNode = net.hosts[issuingID-1]
		issuingNode = net.hosts[issuingID]
		brokerId = topic["brokerId"][1:]
		print(issuingNode)
		print(net.hosts)

		print("Creating topic "+topicName+" at broker "+str(issuingID)+" partition "+str(topicPartition))

		# out = issuingNode.cmd("kafka/bin/kafka-topics.sh --create --bootstrap-server 10.0.0."+str(issuingID)+
		# 	":9092 --replication-factor "+str(topicReplica)+" --partitions " + str(topicPartition) +
		# 	" --topic "+topicName, shell=True)
		out = issuingNode.cmd("kafka/bin/kafka-topics.sh --create --bootstrap-server 10.0.0."+brokerId+
			":9092 --replication-factor "+str(topicReplica)+" --partitions " + str(topicPartition) +
			" --topic "+topicName, shell=True)
```
2. spawnProducers() and spawnConsumers() were also changed so that we can set the correct IP address for the
bootstrap-server and also setting the desired parameters in the producers.
```python
spawnProducers()
while prodInstance <= int(nProducerInstances):
				if producerType == 'CUSTOM':
					# node.popen("python3 "+ producerPath +" " +nodeID+" "+str(prodInstance)+" "+str(brokerId)+" &", shell=True)
					node.popen("python3 "+producerPath+" "+nodeID+" "+str(prodInstance)+" "+str(brokerId)+" "+str(mRate)\
						+" "+str(nTopics)+" "+str(compression)+" "+str(batchSize)+" "+str(linger)\
						+" "+str(bufferMemory)+" &", shell=True)

-----------------------------------------------------------------------------------------------------------------------------
spawnConsumers()
while consInstance <= int(nConsumerInstances):
   if consumerType == 'CUSTOM':
      node.popen("python3 "+consumerPath+" "+str(node.name)+" "+str(consInstance)+" "+str(brokerId)+" &", shell=True)
```
### military-consumerSingle.py
1. added brokerId so that consumer can subscribe to the right broker and also number of topics is changed to 1

### military-data-producer.py
1. Code added to take the parameters from runLoad() function where military-data-producer.py is being called
so that we can set producer configuration


## Usage

In order to use this code you can run this command:
```python
sudo python3 main.py use-cases/disconnection/millitary-coordination/input.graphml --time 10
```
## Issues

1. in military-consumerSingle.py, I had to comment out group_id and number of instances
when the KafkaConsumer was being created. Without commenting this part, the consumer will
not be able to read from the broker
```python
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
```
2. When we set the zookeeper only in the node that broker was set up, we get an error indicating 
that one zookeeper is not enough and zookeeper address can't be set. On the other hand we can't have 
2 zookeepers as the number of zookeepers need to be odd. So I had to set up zookeeper in all three hosts



