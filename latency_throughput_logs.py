import numpy as np
from datetime import datetime, timedelta

interval = 5
consLogs = []
prodCount = 0

def plotLatencyScatter(logDir):
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
                 latencyYAxis.append(float(firstSplit[1][0:2])*60.0 + float(firstSplit[1][3:12]))
    return latencyYAxis

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


def overheadCheckPlot(portFlag, msgSize):
    
    allBandwidth = []
    countX = 0
    
    portParams = [(1,1),(2,1),(3,1),(4,1),(5,1),(6,1),(7,1),(8,1),(9,1),(10,1),
                  (1,2),(2,2),(1,3),(3,3),(1,4),(4,4),(1,5),(5,5),(1,6),(6,6),
                  (1,7),(7,7),(1,8),(8,8),(1,9),(9,9),(1,10),(10,10)]
    for ports in portParams:
        portId, switchId = ports
    
        bandwidth, occurrence, maxBandwidth = readThroughput(switchId,portId, portFlag)
        
        if countX == 0:
            countX = occurrence
        
        if len(bandwidth)<countX:
            for k in range(countX-len(bandwidth)):
                bandwidth.append(0)                    #filling with 0's to match up the length
            
        allBandwidth.append(bandwidth)

    bandwidthSum = []
    bandwidthSumLeaderLess = []
    for i in range(countX):
        valWithLeader = 0
#         valWithoutLeader = 0
        for j in range(10):
            valWithLeader = valWithLeader+allBandwidth[j][i]
#             if (j+1) not in leaderReplicaList:         #to skip the leader replica curves
#                 valWithoutLeader = valWithoutLeader+allBandwidth[j][i]
        
        bandwidthSum.append(valWithLeader)
#         bandwidthSumLeaderLess.append(valWithoutLeader)
        
    timeList = list(range(0,countX*interval,interval))


    newBandwidthSum = [x / 1000000 for x in bandwidthSum]
    
    return newBandwidthSum

def plotAggregatedBandwidth():   
    msgSize = 10
    return overheadCheckPlot("bytes", msgSize)

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

def getProdDetails(prod, logDir, nConsumer, consDetails):
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