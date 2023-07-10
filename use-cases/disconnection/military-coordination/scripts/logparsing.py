
class ProducerLog():

	def __init__(self):
		super(ProducerLog, self).__init__()

	
	"""Return all entries from a producer log as a
	(message time, topic id, msg id) list"""
	def getProdData(self, filePath):

		prodData = []
    
		with open(filePath) as f:
			for line in f:

				if "Topic-name:" in line:
					msgProdTime = line.split(" INFO:Topic-name:")[0][:-1]

					topicSplit = line.split("topic-")
					topicID = topicSplit[1].split(";")[0]

					msgIDSplit = line.split("Message ID: ")
					msgID = msgIDSplit[1].split(";")[0]

					msgData = [msgProdTime, topicID, msgID]
					prodData.append(msgData)

		return prodData
		
	
	def getBrokerConfirmations(self, filePath):
	
		brokerConfirmations = []
		
		with open(filePath) as f:
			for line in f:
			
				if "INFO:Message not produced." in line:
					msgIDSplit = line.split("ID: ")
					msgID = msgIDSplit[1].split(";")[0]
					
					confirmation = [msgID, "0"]
					brokerConfirmations.append(confirmation)

				elif "INFO:Produced message ID:" in line:
					msgIDSplit = line.split("Produced message ID: ")
					msgID = msgIDSplit[1].split(";")[0]
					
					confirmation = [msgID, "1"]
					brokerConfirmations.append(confirmation)
					
		return brokerConfirmations	
		
		
	def getAllBrokerConfirmations(self, prodDir, prodDetails):
	
		allBrokerConfirmations = []
		
		for prod in prodDetails:
			brokerConfirmations = self.getBrokerConfirmations(prodDir+'prod-node'+str(prod['prodNodeID'])\
										+'-instance'+str(prod['prodInstID'])+'.log')
			allBrokerConfirmations.append(brokerConfirmations)

		return allBrokerConfirmations
	

	"""Return a matrix where each line contains all entries 
	(i.e., produced messages) for a given producer"""
	def getAllProdData(self, prodDir, prodDetails):
		
		allProducerData = []

		for prod in prodDetails:
			prodData = self.getProdData(prodDir+'prod-node'+str(prod['prodNodeID'])\
										+'-instance'+str(prod['prodInstID'])+'.log')
			allProducerData.append(prodData)

		return allProducerData


	"""Return data from a particular message"""
	def getMsgData(self, prodData, msgID):

		reqMsg = []

		for msg in prodData:
			if msg[2] == msgID.zfill(6):
				reqMsg = msg
				break

		return reqMsg

		
			
        	        

class ConsumerLog():	

	def __init__(self):
		super(ConsumerLog, self).__init__()

	"""Return all entries from a consumer log as a
	(message time, producer id, message id, topic id, offset) list"""
	def getConsData(self, filePath):
    
		consData = []

		with open(filePath) as f:
			#for lineNum, line in enumerate(f,1):         #to get the line number
			for line in f:

				if "Topic: topic-" in line:
					msgConsTime = line.split(" INFO:Prod")[0]

					prodIDSplit = line.split("Prod ID: ")
					prodID = prodIDSplit[1].split(";")[0]

					msgIDSplit = line.split("Message ID: ")
					msgID = msgIDSplit[1].split(";")[0]

					topicSplit = line.split("topic-")
					topicID = topicSplit[1].split(";")[0]

					offsetSplit = line.split("Offset: ")
					offset = offsetSplit[1].split(";")[0]

					msgData = [msgConsTime, prodID, msgID, topicID, offset]
					consData.append(msgData)

		return consData



	def getAllConsData(self, consDir, consDetails):
		
		allConsumerData = []

		for cons in consDetails:
			consData = self.getConsData(consDir+'cons-node'+str(cons['consNodeID'])\
				+'-instance'+str(cons['consInstID'])+'.log')
			allConsumerData.append(consData)

		return allConsumerData


	"""Get all messages received from a given producer"""
	def getAllMsgFromProd(self, consData, prodID):

		msgList = []

		for msg in consData:
			if msg[1] == prodID:
				msgList.append(msg)

		return msgList
		
		
	
	def getGroupCoordinator(self, filePath):

		with open(filePath) as f:

			for line in f:

				if "INFO:Group coordinator for group" in line:

					coordinatorIDSplit = line.split("nodeId='coordinator-")
					coordinatorID = coordinatorIDSplit[1].split("\',")[0]

		return coordinatorID
		
		
	def getAllGroupCoordinators(self, consDir, consDetails):

		allCoordinators = []

		for cons in consDetails:
			groupCoordinator = self.getGroupCoordinator(consDir+'cons-node'+str(cons['consNodeID'])\
				+'-instance'+str(cons['consInstID'])+'.log')

			allCoordinators.append(groupCoordinator)

		return allCoordinators