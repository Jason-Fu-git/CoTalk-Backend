import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_group_name=f'chat_simple'
        #加入群组
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()
    
    def disconnect(self, close_code):
        #离开群组
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        print("Backend ChatConsumer receive: "+text_data)
        text_data_json=json.loads(text_data)
        message=text_data_json['message']
        #将消息发到群组
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type' : 'chat_message',
                'message' : message,
            }
        )
        self.send(text_data=json.dumps({'message':message}))
    
    def chat_message(self, event):
        self.send(text_data=json.dumps(event))