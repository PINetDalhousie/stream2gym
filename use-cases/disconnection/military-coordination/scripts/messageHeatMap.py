# sudo python3 use-cases/disconnection/millitary-coordination/GD-scenario/scripts/messageHeatMap.py --topic 2 --number-of-producers 10 --number-of-consumers 10 --log-dir logs/output
#!/usr/bin/env python3

import sys
import os
import argparse

import logparsing
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

parser = argparse.ArgumentParser(description='Script for visualizing message delivery.')
parser.add_argument('--log-dir', dest='logDir', type=str, help='Log directory')
parser.add_argument('--number-of-producers', dest='nProducer', type=int, default=0, help='Number of producers')
parser.add_argument('--number-of-consumers', dest='nConsumer', type=int, default=0, help='Number of consumers')
parser.add_argument('--topic', dest='nTopic', type=int, default=0, help='Number of topics')

args = parser.parse_args()

logDir = args.logDir
nProducer = args.nProducer
nConsumer = args.nConsumer
nTopic = args.nTopic

prodDetails = []
consDetails = []
for i in range(nProducer):
    prodInstance = {'prodNodeID':i+1, 'prodInstID':1}
    prodDetails.append(prodInstance)

for i in range(nConsumer):
    consInstance = {'consNodeID':i+1, 'consInstID':1}
    consDetails.append(consInstance)

# prodDetails = [{'prodNodeID':1, 'prodInstID':1}, {'prodNodeID':2, 'prodInstID':1}, {'prodNodeID':3, 'prodInstID':1}]
# consDetails = [{'consNodeID':1, 'consInstID':1}, {'consNodeID':2, 'consInstID':1}, {'consNodeID':3, 'consInstID':1}]
# nProducer = len(prodDetails)
# nConsumer = len(consDetails)
# logDir = '/home/monzurul/Desktop/stream2gym/logs/output/'
# nTopic = 1
# print(nProducer)

#Create heat maps for all producers
heatMapDir = logDir+'/msg-delivery/'
failedMsgDir = logDir+'/failed-messages/'
bkConfirmationDir = logDir+'/broker-confirmation/'
os.system("sudo rm -rf "+heatMapDir+"; sudo mkdir -p "+heatMapDir)
os.system("sudo rm -rf "+failedMsgDir+"; sudo mkdir -p "+failedMsgDir)
os.system("sudo rm -rf "+bkConfirmationDir+"; sudo mkdir -p "+bkConfirmationDir)

params = {  
			'num_consumers' : nConsumer,
			'cons_dir' : logDir+'/cons/',
			'num_producers' : nProducer,
			'prod_dir' : logDir+'/prod/',
			'num_topics' : nTopic
		}
		
prodLog = logparsing.ProducerLog()
consLog = logparsing.ConsumerLog()
		
#Plot broker confirmations
brokerConfirmations = prodLog.getAllBrokerConfirmations(params['prod_dir'], prodDetails)

for producer in range(nProducer):

	confirmationHeatData = []

	for confirmation in brokerConfirmations[producer]:
		confirmationHeatData.append(int(confirmation[1]))

	dfConf = pd.DataFrame(confirmationHeatData, columns=["Prod"])

	sns.heatmap(dfConf.T, vmin=0, vmax=255)

	plt.xlabel('Message ID')
	plt.title("Producer " + str(producer+1) + "- Broker confirmations")

	# os.makedirs("broker-confirmation", exist_ok=True)

	plt.savefig(bkConfirmationDir+"producer-"+str(producer+1)+".png",format='png', bbox_inches="tight")

	#plt.close()
	plt.cla()
	plt.clf()  
	

#Initialize topic colors
topicColors = {}
colorInc = round(255 / params['num_topics'])

for i in range(params['num_topics']):
	topicColors[i] = colorInc*i

#Read producer data
prodData = prodLog.getAllProdData(params['prod_dir'], prodDetails)
#Read consumer data
consData = consLog.getAllConsData(params['cons_dir'], consDetails)

#Create heat maps for all producers
iterCount = 1

for producer in range(nProducer):

	#Create heat map
	rawHeatData = []
	
	#Retrieve message confirmation info
	confirmations = brokerConfirmations[producer]

	#Initialize heat matrix: [consumer, prod msg]
	for i in range(nConsumer):
		recvMsg = []
		prodMsg = [0]*len(prodData[producer])
		recvMsg.append(prodMsg)

		rawHeatData.append(prodMsg)
	
	#Fill heat matrix with message delivery information
	for consumer in range(nConsumer):
	
		#Read consumer data
		consID = consumer

		rawRecvMsgs = consLog.getAllMsgFromProd( consData[consumer], str(producer+1).zfill(2) )

		#Fill heat matrix with received messages
		for msg in rawRecvMsgs:
			msgID = msg[2]
			rawHeatData[consID][int(msgID)] = 255

		#Color unreceived messages according to their topic
		consHeatMap = rawHeatData[consumer]

		missingMsgs = []
		i = 0

		for msg in consHeatMap:
			if msg == 0:
				missingMsgs.append(i)

			i += 1

		missingTopic = []

		for miss in missingMsgs:
			missMsg = prodLog.getMsgData(prodData[producer], str(miss))
			missTopic = missMsg[1]

			rawHeatData[consID][miss] = topicColors[int(missTopic)]
			
		#Mark unconfirmed messages as sent
		for conf in confirmations:
			if conf[1] == "0":
				if rawHeatData[consID][int(conf[0])] == 255:
					print("ERROR: inconsistency found. Check message ", conf[0], ", producer ", str(producer), ", consumer ", str(consID))
				else:
					#Message not confirmed. Mark as sent.
					rawHeatData[consID][int(conf[0])] = 255

	# os.makedirs("failed-messages", exist_ok=True)
	
	f = open(failedMsgDir+"fail-log-prod-"+str(producer+1)+".txt", "w")

	f.write("Producer "+str(producer)+"\n")
	f.write("=============================\n")
	
	for consumer in range(nConsumer): 

		f.write("Consumer "+str(consumer)+"\n")
		f.write("-------------\n")

		for msgIdx in range(len(rawHeatData[consumer])):
			if rawHeatData[consumer][msgIdx] != 255 and msgIdx < 9000:
				f.write("Index: "+str(msgIdx)+"\n")
		f.write("**************\n")
	f.close()

	#Plot heatmap
	df = pd.DataFrame(rawHeatData, columns=[i for i in range(len(prodData[producer]))])

	sns.heatmap(df, vmin=0, vmax=255)

	plt.xlabel('Message ID')
	plt.ylabel('Consumer')
	plt.title("Producer " + str(producer+1) + "- Message delivery")

	# os.makedirs("msg-delivery", exist_ok=True)

	# plt.savefig("msg-delivery/producer-"+str(producer+1)+".png",format='png', bbox_inches="tight")
	plt.savefig(heatMapDir+"producer-"+str(producer+1)+".png",format='png', bbox_inches="tight")

	#plt.close()
	plt.cla()
	plt.clf()  
	
	#Show processing status
	print('Processing: '+str((iterCount/params['num_producers'])*100.0)+'% complete')
	iterCount += 1

#	plt.show()