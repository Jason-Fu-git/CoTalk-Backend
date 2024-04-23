from django.test import TestCase
from channels.testing import WebsocketCommunicator
from .consumers import WSConsumer
from channels.db import database_sync_to_async
from user.models import User
from chat.models import Chat, Membership


class WSTests(TestCase):
    # 执行此单元测试前一定要运行redis!
    def setUp(self):
        # create 2 users and 1 chat
        self.admin = User.objects.create(user_name='admin', password='admin_pwd')
        self.guest = User.objects.create(user_name='guest', password='guest_pwd')
        self.chat = Chat.objects.create(chat_name='test_chat', is_private=False)
        Membership.objects.create(user=self.admin, chat=self.chat, privilege='O', is_approved=True)
        Membership.objects.create(user=self.guest, chat=self.chat, privilege='M', is_approved=True)

        # login 2 users
        response = self.client.post('/api/user/login', data={'user_name': 'admin', 'password': 'admin_pwd'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.admin_token = response.json()['token']

        response = self.client.post('/api/user/login', data={'user_name': 'guest', 'password': 'guest_pwd'},
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.guest_token = response.json()['token']

    def register(self, user_name, password, user_email=None, user_icon=None):
        body = {}
        if user_name is not None:
            body['user_name'] = user_name

        if password is not None:
            body['password'] = password

        if user_email is not None:
            body['user_email'] = user_email

        if user_icon is not None:
            body['user_icon'] = user_icon

        return self.client.post('/api/user/register', data=body, format='multipart')

    async def test_ws_success(self):
        admin_response = await database_sync_to_async(self.register)(user_name='test_ws_success_admin',
                                                                     password='admin_pwd')
        self.assertEqual(admin_response.status_code, 200)
        token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']
        communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                             f'/ws/?Authorization={token}&user_id={admin_id}')
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_ws_fail(self):
        admin_response = await database_sync_to_async(self.register)(user_name='test_ws_fail_admin',
                                                                     password='admin_pwd')
        self.assertEqual(admin_response.status_code, 200)
        guest_response = await database_sync_to_async(self.register)(user_name='test_ws_fail_guest',
                                                                     password='guest_pwd')
        self.assertEqual(guest_response.status_code, 200)
        guest_id = guest_response.json()['user_id']
        admin_token = admin_response.json()['token']
        # none-query string
        communicator1 = WebsocketCommunicator(WSConsumer.as_asgi(),
                                              f'/ws/')
        connected, _ = await communicator1.connect()
        self.assertFalse(connected)
        await communicator1.disconnect()
        # wrong query string
        communicator2 = WebsocketCommunicator(WSConsumer.as_asgi(),
                                              f'/ws/?user_id=123456789')
        connected, _ = await communicator2.connect()
        self.assertFalse(connected)
        await communicator2.disconnect()

        communicator3 = WebsocketCommunicator(WSConsumer.as_asgi(),
                                              f'/ws/?Authorization={admin_token}')
        connected, _ = await communicator3.connect()
        self.assertFalse(connected)
        await communicator3.disconnect()
        # wrong token
        communicator4 = WebsocketCommunicator(WSConsumer.as_asgi(),
                                              f'/ws/?user_id={guest_id}&Authorization={admin_token}')
        connected, _ = await communicator4.connect()
        self.assertFalse(connected)
        await communicator4.disconnect()

    async def test_ws_twice(self):
        admin_response = await database_sync_to_async(self.register)(user_name='test_ws_twice_admin',
                                                                     password='admin_pwd')
        self.assertEqual(admin_response.status_code, 200)
        token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']
        communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                             f'/ws/?Authorization={token}&user_id={admin_id}')
        connected1, _ = await communicator.connect()
        self.assertTrue(connected1)

        communicator1 = WebsocketCommunicator(WSConsumer.as_asgi(),
                                              f'/ws/?Authorization={token}&user_id={admin_id}')
        connected2, _ = await communicator1.connect()
        self.assertFalse(connected2)

        await communicator.disconnect()
        await communicator1.disconnect()

        communicator2 = WebsocketCommunicator(WSConsumer.as_asgi(),
                                              f'/ws/?Authorization={token}&user_id={admin_id}')
        connected3, _ = await communicator2.connect()
        # self.assertTrue(connected3)
        await communicator2.disconnect()

    async def test_friend_request_success(self):
        admin_response = await database_sync_to_async(self.register)(user_name='test_friend_request_success_admin',
                                                                     password='admin_pwd')
        self.assertEqual(admin_response.status_code, 200)
        admin_token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']
        admin_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                   f'/ws/?Authorization={admin_token}&user_id={admin_id}')
        connected, _ = await admin_communicator.connect()
        self.assertTrue(connected)

        guest_response = await database_sync_to_async(self.register)(user_name='test_friend_request_success_guest',
                                                                     password='guest_pwd')
        self.assertEqual(guest_response.status_code, 200)
        guest_token = guest_response.json()['token']
        guest_id = guest_response.json()['user_id']

        guest_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                   f'/ws/?Authorization={guest_token}&user_id={guest_id}')
        connected, _ = await guest_communicator.connect()
        self.assertTrue(connected)

        # send http request
        response = await database_sync_to_async(self.client.put)(path=f'/api/user/private/{admin_id}/friends',
                                                                 data={
                                                                     'friend_id': guest_id,
                                                                     'approve': 'true'
                                                                 },
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 200)

        # guest receive message
        response = await guest_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'make request')
        self.assertEqual(response['user_id'], admin_id)

        # guest accepts
        response = await database_sync_to_async(self.client.put)(path=f'/api/user/private/{guest_id}/friends',
                                                                 data={
                                                                     'friend_id': admin_id,
                                                                     'approve': 'true'
                                                                 },
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 200)

        # admin receive message
        response = await admin_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'accept request')
        self.assertEqual(response['user_id'], guest_id)

        # they are friends
        response = await database_sync_to_async(self.client.get)(path=f'/api/user/private/{guest_id}/friends',
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(len(response.json()['friends']), 1)

        # guest deleted admin
        response = await database_sync_to_async(self.client.put)(path=f'/api/user/private/{guest_id}/friends',
                                                                 data={
                                                                     'friend_id': admin_id,
                                                                     'approve': 'false'
                                                                 },
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=guest_token)

        # admin receive message
        response = await admin_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'delete')
        self.assertEqual(response['user_id'], guest_id)

        # they are not friends
        response = await database_sync_to_async(self.client.get)(path=f'/api/user/private/{guest_id}/friends',
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(len(response.json()['friends']), 0)

        # admin tries to make friend with guest again
        response = await database_sync_to_async(self.client.put)(path=f'/api/user/private/{admin_id}/friends',
                                                                 data={
                                                                     'friend_id': guest_id,
                                                                     'approve': 'true'
                                                                 },
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 200)

        # guest receive message
        response = await guest_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'make request')
        self.assertEqual(response['user_id'], admin_id)

        # guest rejects
        response = await database_sync_to_async(self.client.put)(path=f'/api/user/private/{guest_id}/friends',
                                                                 data={
                                                                     'friend_id': admin_id,
                                                                     'approve': 'false'
                                                                 },
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 200)

        # admin receive message
        response = await admin_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'reject request')
        self.assertEqual(response['user_id'], guest_id)

        # they are not friends
        response = await database_sync_to_async(self.client.get)(path=f'/api/user/private/{admin_id}/friends',
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(len(response.json()['friends']), 0)

        await guest_communicator.disconnect()
        await admin_communicator.disconnect()

    async def test_chat_create_invitation_success(self):
        socrates_response = await database_sync_to_async(self.register)('socrates', 'socrates_pwd')
        self.assertEqual(socrates_response.status_code, 200)
        socrates_token = socrates_response.json()['token']
        socrates_id = socrates_response.json()['user_id']

        plato_response = await database_sync_to_async(self.register)('plato', 'plato_pwd')
        self.assertEqual(plato_response.status_code, 200)
        plato_token = plato_response.json()['token']
        plato_id = plato_response.json()['user_id']

        aristotle_response = await database_sync_to_async(self.register)('aristotle', 'aristotle_pwd')
        self.assertEqual(aristotle_response.status_code, 200)
        aristotle_token = aristotle_response.json()['token']
        aristotle_id = aristotle_response.json()['user_id']

        socrates_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                      f'/ws/?Authorization={socrates_token}&user_id={socrates_id}')
        connected, _ = await socrates_communicator.connect()
        self.assertTrue(connected)

        aristotle_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                       f'/ws/?Authorization={aristotle_token}&user_id={aristotle_id}')
        connected, _ = await aristotle_communicator.connect()
        self.assertTrue(connected)

        plato_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                   f'/ws/?Authorization={plato_token}&user_id={plato_id}')
        connected, _ = await plato_communicator.connect()
        self.assertTrue(connected)

        # socrates created a new chat
        response = await database_sync_to_async(self.client.post)(path=f'/api/chat/create',
                                                                  data={
                                                                      "user_id": socrates_id,
                                                                      "chat_name": "Athens",
                                                                      "members": [
                                                                          aristotle_id,
                                                                          plato_id
                                                                      ]
                                                                  }, content_type='application/json',
                                                                  HTTP_AUTHORIZATION=socrates_token)

        self.assertEqual(response.status_code, 200)
        chat_id = response.json()['chat_id']

        # check whether aristotle and plato received the invitation
        response = await aristotle_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['user_id'], socrates_id)
        self.assertEqual(response['chat_id'], chat_id)

        response = await plato_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'make invitation')
        self.assertEqual(response['chat_id'], chat_id)

        await socrates_communicator.disconnect()
        await plato_communicator.disconnect()
        await aristotle_communicator.disconnect()

    async def test_chat_invitation_success(self):
        socrates_response = await database_sync_to_async(self.register)('socrates', 'socrates_pwd')
        self.assertEqual(socrates_response.status_code, 200)
        socrates_token = socrates_response.json()['token']
        socrates_id = socrates_response.json()['user_id']

        plato_response = await database_sync_to_async(self.register)('plato', 'plato_pwd')
        self.assertEqual(plato_response.status_code, 200)
        plato_token = plato_response.json()['token']
        plato_id = plato_response.json()['user_id']

        aristotle_response = await database_sync_to_async(self.register)('aristotle', 'aristotle_pwd')
        self.assertEqual(aristotle_response.status_code, 200)
        aristotle_token = aristotle_response.json()['token']
        aristotle_id = aristotle_response.json()['user_id']

        socrates_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                      f'/ws/?Authorization={socrates_token}&user_id={socrates_id}')
        connected, _ = await socrates_communicator.connect()
        self.assertTrue(connected)

        aristotle_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                       f'/ws/?Authorization={aristotle_token}&user_id={aristotle_id}')
        connected, _ = await aristotle_communicator.connect()
        self.assertTrue(connected)

        plato_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                   f'/ws/?Authorization={plato_token}&user_id={plato_id}')
        connected, _ = await plato_communicator.connect()
        self.assertTrue(connected)

        _chat = await self.create_a_chat('Athens', [socrates_id, plato_id])
        self.assertEqual(_chat.chat_name, 'Athens')

        # socrates sends a chat invitation to aristotle
        response = await database_sync_to_async(self.client.put)(f'/api/chat/{_chat.chat_id}/members',
                                                                 data={'user_id': socrates_id,
                                                                       'member_id': aristotle_id,
                                                                       'approve': True},
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)

        # check websocket
        response = await aristotle_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'make invitation')
        self.assertEqual(response['user_id'], socrates_id)
        self.assertEqual(response['chat_id'], _chat.chat_id)

        # aristotle accepts
        response = await database_sync_to_async(self.client.put)(f'/api/chat/{_chat.chat_id}/members',
                                                                 data={'user_id': aristotle_id,
                                                                       'member_id': aristotle_id,
                                                                       'approve': True},
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(response.status_code, 200)

        # plato kicked aristotle out
        response = await database_sync_to_async(self.client.put)(f'/api/chat/{_chat.chat_id}/members',
                                                                 data={'user_id': plato_id,
                                                                       'member_id': aristotle_id,
                                                                       'approve': False},
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 200)

        # check websocket
        response = await aristotle_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'kicked out')
        self.assertEqual(response['user_id'], plato_id)
        self.assertEqual(response['chat_id'], _chat.chat_id)

        await socrates_communicator.disconnect()
        await plato_communicator.disconnect()
        await aristotle_communicator.disconnect()

    async def test_change_privilege_success(self):
        socrates_response = await database_sync_to_async(self.register)('socrates', 'socrates_pwd')
        self.assertEqual(socrates_response.status_code, 200)
        socrates_token = socrates_response.json()['token']
        socrates_id = socrates_response.json()['user_id']

        plato_response = await database_sync_to_async(self.register)('plato', 'plato_pwd')
        self.assertEqual(plato_response.status_code, 200)
        plato_token = plato_response.json()['token']
        plato_id = plato_response.json()['user_id']

        aristotle_response = await database_sync_to_async(self.register)('aristotle', 'aristotle_pwd')
        self.assertEqual(aristotle_response.status_code, 200)
        aristotle_token = aristotle_response.json()['token']
        aristotle_id = aristotle_response.json()['user_id']

        socrates_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                      f'/ws/?Authorization={socrates_token}&user_id={socrates_id}')
        connected, _ = await socrates_communicator.connect()
        self.assertTrue(connected)

        aristotle_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                       f'/ws/?Authorization={aristotle_token}&user_id={aristotle_id}')
        connected, _ = await aristotle_communicator.connect()
        self.assertTrue(connected)

        plato_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                   f'/ws/?Authorization={plato_token}&user_id={plato_id}')
        connected, _ = await plato_communicator.connect()
        self.assertTrue(connected)

        _chat = await self.create_a_chat('Athens', [socrates_id, plato_id])
        self.assertEqual(_chat.chat_name, 'Athens')

        # socrates attempts to change plato's privilege
        response = await database_sync_to_async(self.client.put)(f'/api/chat/{_chat.chat_id}/management',
                                                                 data={
                                                                     'user_id': socrates_id,
                                                                     'member_id': plato_id,
                                                                     'change_to': 'member'
                                                                 }, content_type='application/json',
                                                                 HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)

        # get websocket
        response = await plato_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'change to member')
        self.assertEqual(response['chat_id'], _chat.chat_id)

        await socrates_communicator.disconnect()
        await plato_communicator.disconnect()
        await aristotle_communicator.disconnect()

    async def test_message_success(self):
        """
        test websocket functionality of post/read/delete message
        """

        # connect 2 communicators
        admin_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                   f'/ws/?Authorization={self.admin_token}&user_id={self.admin.user_id}')
        connected, _ = await admin_communicator.connect()
        self.assertTrue(connected)

        guest_communicator = WebsocketCommunicator(WSConsumer.as_asgi(),
                                                   f'/ws/?Authorization={self.guest_token}&user_id={self.guest.user_id}')
        connected, _ = await guest_communicator.connect()
        self.assertTrue(connected)

        # admin send a message
        response = await database_sync_to_async(self.client.post)('/api/message/send',
                                                                  data={
                                                                      'user_id': self.admin.user_id,
                                                                      'chat_id': self.chat.chat_id,
                                                                      'msg_text': 'Hello World!',
                                                                      'msg_type': 'text',
                                                                  }, format='multipart',
                                                                  HTTP_AUTHORIZATION=self.admin_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        # check guest's websocket
        response = await guest_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'send message')
        self.assertEqual(response['msg_id'], msg_id)
        self.assertEqual(response['user_id'], self.admin.user_id)
        self.assertEqual(response['chat_id'], self.chat.chat_id)
        # skip admin's websocket
        response = await admin_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'send message')

        # guest read a message
        response = await database_sync_to_async(self.client.put)(f'/api/message/{msg_id}/management',
                                                                 data={
                                                                     'user_id': self.guest.user_id,
                                                                 },
                                                                 content_type='application/json',
                                                                 HTTP_AUTHORIZATION=self.guest_token)
        self.assertEqual(response.status_code, 200)

        # check admin's websocket
        response = await admin_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'read message')
        self.assertEqual(response['msg_id'], msg_id)
        self.assertEqual(response['user_id'], self.guest.user_id)

        # skip guest's websocket
        response = await guest_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'read message')

        # admin withdraw the message
        response = await database_sync_to_async(self.client.delete)(f'/api/message/{msg_id}/management',
                                                                    data={
                                                                        'user_id': self.admin.user_id,
                                                                        'is_remove': True
                                                                    },
                                                                    content_type='application/json',
                                                                    HTTP_AUTHORIZATION=self.admin_token)
        self.assertEqual(response.status_code, 200)

        # check guest's websocket
        response = await guest_communicator.receive_json_from(timeout=5)
        self.assertEqual(response['status'], 'withdraw message')

        await admin_communicator.disconnect()
        await guest_communicator.disconnect()

    @database_sync_to_async
    def create_a_chat(self, chat_name, user_ids):
        _chat = Chat.objects.create(chat_name=chat_name, is_private=False)
        _chat.save()
        for user_id in user_ids:
            Membership.objects.create(user_id=user_id, chat=_chat, privilege='A', is_approved=True).save()
        membership = Membership.objects.get(user_id=user_ids[0], chat=_chat)
        membership.privilege = 'O'
        membership.save()
        return _chat
