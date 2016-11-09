from django.shortcuts import render
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
import json,wikipedia,urllib,os
from chatbot import Chat,reflections,multiFunctionCall
from .models import *
from django.db.utils import OperationalError,ProgrammingError
from background_task import background
import requests,datetime

# Create your views here.

@login_required
def index(request):
    return render(request,"index.html")

def about(query,qtype=None):
    service_url = 'https://kgsearch.googleapis.com/v1/entities:search'
    params = {
        'query': query,
        'limit': 10,
        'indent': True,
        'key': api_key,
    }
    url = service_url + '?' + urllib.urlencode(params)
    response = json.loads(urllib.urlopen(url).read())
    if not len(response['itemListElement']):
        return "sorry, I don't know about "+query +"\nIf you know about "+query+" please tell me."
    result = ""
    if len(response['itemListElement'])==1:
        if "detailedDescription" in response['itemListElement'][0]['result']:
            return response['itemListElement'][0]['result']['detailedDescription']["articleBody"]
        else:
            return response['itemListElement'][0]['result']['name'] +" is a " +\
                   response['itemListElement'][0]['result']["description"]
    for element in response['itemListElement']:
      try:result += element['result']['name'] + "->" +element['result']["description"]+"\n"
      except:pass
    return result

def getType(l):
    try:
        l.remove("Thing")
        return "("+l[0]+")"
    except:
        return ""

def tellMeAbout(query,sessionID="general"):
    return about(query)

def whoIs(query,sessionID="general"):
    return about(query,qtype="Person")

def whereIs(query,sessionID="general"):
    return about(query,qtype="Place")

def whatIs(query,sessionID="general"):
    try:
        return wikipedia.summary(query)
    except:
        for newquery in wikipedia.search(query):
            try:
                return wikipedia.summary(newquery)
            except:
                pass
    return about(query)

call = multiFunctionCall({"whoIs":whoIs,
                          "whatIs":whatIs,
                          "whereIs":whereIs,
                          "tellMeAbout":tellMeAbout})

class UserMemory:

    def __init__(self,senderID, *args, **kwargs):
        self.senderID=senderID
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        try:return Memory.objects.get(sender__messengerSenderID=self.senderID,key=key).value
        except:raise KeyError(key)

    def __setitem__(self, key, val):
        try:
            memory = Memory.objects.get(sender__messengerSenderID=self.senderID,key=key)
            memory.value = val
            Memory.save()
        except:
            Memory.objects.create(sender__messengerSenderID=self.senderID,key=key,value=value)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v
    
    def __delitem__(self, key):
        try:return Memory.objects.get(sender__messengerSenderID=self.senderID,key=key).delete()
        except:raise KeyError(key)

    def __contains__(self, key):
        return Memory.objects.filter(sender__messengerSenderID=self.senderID,key=key)
        
        
    
    
class UserConversation:

    def __init__(self,senderID, *args):
        self.senderID=senderID
        self.extend(list(*args))

    def __getitem__(self, index):
        try:
            conv = Conversation.objects.filter(sender__messengerSenderID=self.senderID)
            return (conv[index] if index >=0 else conv.order_by('-id')[-index-1]).message
        except:raise IndexError("list index out of range")

    def __setitem__(self, index, message):
        try:
            convs = Conversation.objects.filter(sender__messengerSenderID=self.senderID)
            conv = (convs[index] if index <0 else convs.order_by('-id')[-index])
            conv.message = message
            conv.save()
        except:raise IndexError("list assignment index out of range")

    def extend(self, items):
        for item in items:
            self.append(item)
            
    def append(self, message):
        Conversation.objects.create(sender=Sender.objects.get(messengerSenderID=self.senderID),message=message)
    
    def __delitem__(self, index):
        try:
            convs = Conversation.objects.filter(sender__messengerSenderID=self.senderID)
            (convs[index] if index <0 else convs.order_by('-id')[-index]).delete()
        except:raise IndexError("list index out of range")
        
        
    def pop(self):
        try:
            Conversation.objects.filter(sender__messengerSenderID=self.senderID)
            conv = convs.order_by('-id')[0]
            message = conv.message
            conv.delete()
            return message
        except:IndexError("pop from empty list")

    def __contains__(self, message):
        return Conversation.objects.filter(sender__messengerSenderID=self.senderID,message=message)

class UserTopic:

    def __init__(self,*args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, senderID):
        try:
            return Sender.objects.get(messengerSenderID=senderID).topic
        except:raise KeyError(key)

    def __setitem__(self, senderID, topic):
        try:
            sender = Sender.objects.get(messengerSenderID=senderID)
            sender.topic = topic
            sender.save()
        except:Sender.objects.create(messengerSenderID=senderID,topic = topic)
    
    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v
    
    def __delitem__(self, senderID):
        try:return Sender.objects.get(messengerSenderID=senderID).delete()
        except:pass
        
    def __contains__(self, senderID):
        return Sender.objects.filter(messengerSenderID=senderID)   
        
class UserSession:

    def __init__(self,objClass, *args, **kwargs):
        self.objClass = objClass
        self.update(*args, **kwargs)

    def __getitem__(self, senderID):
        try:
            return self.objClass(Sender.objects.get(messengerSenderID=senderID).messengerSenderID)
        except:raise KeyError(senderID)

    def __setitem__(self, senderID, val):
        Sender.objects.get_or_create(messengerSenderID=senderID)
        self.objClass(senderID,val)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v
    
    def __delitem__(self, senderID):
        try:return Sender.objects.get(messengerSenderID=senderID).delete()
        except:raise KeyError(key)
        
    def __contains__(self, senderID):
        return Sender.objects.filter(messengerSenderID=senderID)


class myChat(Chat):

    def __init__(self, *arg, **karg):
        super(myChat, self).__init__(*arg, **karg) 
        self._memory = UserSession(UserMemory,self._memory)
        self.conversation = UserSession(UserConversation,self.conversation)
        self.topic.topic = UserTopic(self.topic.topic)
        #self._pairs = {'*':[]}
        #self._reflections = reflections
        #self._regex = self._compile_reflections()
    
try:
    chat=myChat(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "chatbotTemplate",
                           "Example.template"
                           ),
              reflections,
              call=call)

except (OperationalError,ProgrammingError):#No DB exist
    chat =  Chat(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "chatbotTemplate",
                           "Example.template"
                           ),
              reflections,
              call=call)

    
def initiateChat(senderID):
    message = 'Welcome to NLTK-Chat demo.'
    chat._startNewSession(senderID)
    chat.conversation[senderID].append(message)
    return message

def respondToClient(senderID,data):
    message = data["text"]
    chat.attr[senderID]={"match":None,"pmatch":None}
    chat.conversation[senderID].append(message)
    message = message.rstrip(".! \n\t")
    result = chat.respond(message,sessionID=senderID)
    chat.conversation[senderID].append(result)
    del chat.attr[senderID]
    return result

def chathandler(request):
    data = json.loads(request.body)
    # Send text message
    if data["type"]=="conversationUpdate":
        return {"status": "","message":return initiateChat(request.user.username)}
    if data["type"]=="message":
        return {"status": "","message":respondToClient(request.user.username,data)}
    return {"status": "Error","message":"Unknown type:'%s'"% data['type']}

@csrf_exempt
@login_required
def webhook(request):
    if request.method=="POST":
        return JsonResponse(chathandler(request))
    return JsonResponse({"status": "Error","message":"Invalid request method"})



