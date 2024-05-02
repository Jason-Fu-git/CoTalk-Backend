from django.test import TestCase
from user.models import User
from chat.models import Chat, Membership
from message.models import Notification, Message


class ChatTestCase(TestCase):

    def setUp(self):
        self.socrates = User.objects.create(
            user_name='socrates',
            password='socrates_pwd',
            description='A great philosopher'
        )
        self.socrates.save()
        self.plato = User.objects.create(
            user_name='plato',
            password='plato_pwd',
        )
        self.plato.save()
        self.aristotle = User.objects.create(
            user_name='aristotle',
            password='aristotle_pwd',
        )
        self.aristotle.save()
        self.athens = Chat.objects.create(
            chat_name='Athens',
            is_private=False
        )
        self.athens.save()
        membership1 = Membership.objects.create(user_id=self.socrates.user_id, chat_id=self.athens.chat_id
                                                , is_approved=True, privilege='O')
        membership1.save()
        membership2 = Membership.objects.create(user_id=self.plato.user_id, chat_id=self.athens.chat_id,
                                                is_approved=True, privilege='A')
        membership2.save()

    # === create chat ===
    def test_create_chat_success(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']
        response = self.client.post('/api/chat/create', data={'user_id': self.socrates.user_id,
                                                              'chat_name': 'Test',
                                                              'members': [self.aristotle.user_id, self.plato.user_id]}
                                    , content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        chat_id = response.json()['chat_id']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['chat_id'], Chat.objects.get(chat_name='Test').chat_id)
        self.assertEqual(Chat.objects.get(chat_name='Test').get_owner().user_id, self.socrates.user_id)
        self.assertEqual(len(Notification.objects.filter(sender_id=self.socrates.user_id)), 2)

        # check invitation
        plato_notification = Notification.objects.get(sender_id=self.socrates.user_id, receiver_id=self.plato.user_id)
        self.assertEqual(eval(plato_notification.content)['status'], 'make invitation')
        self.assertEqual(eval(plato_notification.content)['user_id'], self.socrates.user_id)

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        # accept
        response = self.client.put(f'/api/chat/{chat_id}/members',
                                   data={
                                       'user_id': self.plato.user_id,
                                       'member_id': self.plato.user_id,
                                       'approve': True
                                   }, content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 200)

        # test
        response = self.client.get(f'/api/chat/{chat_id}/members',
                                   data={
                                       'user_id': self.plato.user_id,
                                   }, content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(len(response.json()['members']), 2)

    def test_create_chat_conflict(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']
        response = self.client.post('/api/chat/create', data={'user_id': self.socrates.user_id,
                                                              'chat_name': 'Athens'}
                                    , content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 409)

    def test_create_chat_bad_method(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']
        response = self.client.delete('/api/chat/create', data={'user_id': self.socrates.user_id,
                                                                'chat_name': 'Athens'}
                                      , content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)
        response = self.client.get('/api/chat/create', data={'user_id': self.socrates.user_id,
                                                             'chat_name': 'Athens'}
                                   , content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)
        response = self.client.put('/api/chat/create', data={'user_id': self.socrates.user_id,
                                                             'chat_name': 'Athens'}
                                   , content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)

    def test_create_chat_bad_request(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']
        response = self.client.post('/api/chat/create', data={'user_id': "hello",
                                                              'chat_name': 'Athens'}
                                    , content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/chat/create', data={'user_id': "hello"}
                                    , content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)

    # === chat request ===

    def test_chat_request_success(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        aristotle_response = self.client.post('/api/user/login',
                                              data={'user_name': 'aristotle', 'password': 'aristotle_pwd'},
                                              content_type='application/json')
        aristotle_token = aristotle_response.json()['token']

        # socrates sends a chat invitation to aristotle
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.socrates.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'approve': True},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.athens.get_memberships()), 2)

        # check notification
        aristotle_notification = Notification.objects.get(sender_id=self.socrates.user_id,
                                                          receiver_id=self.aristotle.user_id)
        self.assertEqual(eval(aristotle_notification.content)['status'], 'make invitation')

        # aristotle accepts
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.aristotle.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'approve': True},
                                   content_type='application/json', HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.athens.get_memberships()), 3)

        # check message
        self.assertEqual(len(Message.objects.filter(chat_id=self.athens.chat_id)), 1)

        # plato kicked aristotle out
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.plato.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'approve': False},
                                   content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.athens.get_memberships()), 2)

        # check notification
        plato_notification = Notification.objects.get(sender_id=self.plato.user_id,
                                                      receiver_id=self.aristotle.user_id)
        self.assertEqual(eval(plato_notification.content)['status'], 'kicked out')

        # check message
        self.assertEqual(len(Message.objects.filter(chat_id=self.athens.chat_id)), 2)

        # socrates re-invited aristotle
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.socrates.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'approve': True},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.athens.get_memberships()), 2)

        # however, aristotle rejected
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.aristotle.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'approve': False},
                                   content_type='application/json', HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.athens.get_memberships()), 2)

    def test_member_list_success(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']
        response = self.client.get(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.socrates.user_id},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)
        members = response.json()['members']
        self.assertEqual(len(members), 2)

    def test_chat_request_bad_request(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']
        response = self.client.get(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': 'hello'},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)
        response = self.client.get(f'/api/chat/{self.athens.chat_id}/members',
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.socrates.user_id,
                                         'approve': True},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)

    def test_chat_request_bad_method(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']
        response = self.client.post(f'/api/chat/{self.athens.chat_id}/members',
                                    content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)
        response = self.client.delete(f'/api/chat/{self.athens.chat_id}/members',
                                      content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)

    def test_chat_request_not_found(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        aristotle_response = self.client.post('/api/user/login',
                                              data={'user_name': 'aristotle', 'password': 'aristotle_pwd'},
                                              content_type='application/json')
        aristotle_token = aristotle_response.json()['token']

        response = self.client.put(f'/api/chat/{100000}/members',
                                   data={'user_id': self.socrates.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'approve': True},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 404)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': 10000,
                                         'member_id': self.aristotle.user_id,
                                         'approve': True},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 404)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.socrates.user_id,
                                         'member_id': 100000,
                                         'approve': True},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 404)

    def test_chat_request_no_privilege(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        aristotle_response = self.client.post('/api/user/login',
                                              data={'user_name': 'aristotle', 'password': 'aristotle_pwd'},
                                              content_type='application/json')
        aristotle_token = aristotle_response.json()['token']

        Membership.objects.create(user=self.aristotle, chat=self.athens, is_approved=True, privilege='M')

        # member attempts to delete admin
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.aristotle.user_id,
                                         'member_id': self.plato.user_id,
                                         'approve': False},
                                   content_type='application/json', HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(response.status_code, 401)

        # admin attempts to delete owner
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/members',
                                   data={'user_id': self.plato.user_id,
                                         'member_id': self.socrates.user_id,
                                         'approve': False},
                                   content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 401)

    # === member privilege ===
    def test_member_privilege_change_success(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        # socrates attempts to change plato's privilege
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': self.plato.user_id,
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.athens.get_admins()), 0)

        # get notification
        notification = Notification.objects.get(sender_id=self.socrates.user_id, receiver_id=self.plato.user_id)
        self.assertEqual(eval(notification.content)['status'], 'change to member')

        # get message
        self.assertEqual(Message.objects.get(sender__user_name='system', chat_id=self.athens.chat_id).msg_text,
                         "socrates changed plato's privilege to member.")

        # socrates hand ownership to plato
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': self.plato.user_id,
                                       'change_to': 'owner'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.athens.get_owner().user_id, self.plato.user_id)
        self.assertEqual(Membership.objects.get(user_id=self.socrates.user_id).privilege, 'M')

    def test_chat_management_bad_method(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        # socrates attempts to change plato's privilege
        response = self.client.post(f'/api/chat/{self.athens.chat_id}/management',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'member_id': self.plato.user_id,
                                        'change_to': 'member'
                                    }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': self.plato.user_id,
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)

        response = self.client.delete(f'/api/chat/{self.athens.chat_id}/management',
                                      data={
                                          'user_id': self.socrates.user_id,
                                          'member_id': self.plato.user_id,
                                          'change_to': 'member'
                                      }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 405)

    def test_chat_management_bad_request(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        # socrates attempts to change plato's privilege
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': self.plato.user_id,
                                       'change_to': 'alien'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'member_id': self.plato.user_id,
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': 'self.plato.user_id',
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.put(f'/api/chat/self.athens.chat_id/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': 'self.plato.user_id',
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 400)

    def test_change_privilege_not_found(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        # socrates attempts to change plato's privilege
        response = self.client.put(f'/api/chat/{239182}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': self.plato.user_id,
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 404)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'user_id': 19289,
                                       'member_id': self.plato.user_id,
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 404)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'member_id': 10000000,
                                       'change_to': 'member'
                                   }, content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 404)

    def test_chat_management_no_privilege(self):
        socrates_response = self.client.post('/api/user/login',
                                             data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                             content_type='application/json')
        socrates_token = socrates_response.json()['token']

        plato_response = self.client.post('/api/user/login',
                                          data={'user_name': 'plato', 'password': 'plato_pwd'},
                                          content_type='application/json')
        plato_token = plato_response.json()['token']

        aristotle_response = self.client.post('/api/user/login',
                                              data={'user_name': 'aristotle', 'password': 'aristotle_pwd'},
                                              content_type='application/json')
        aristotle_token = aristotle_response.json()['token']

        Membership.objects.create(user=self.aristotle, chat=self.athens, is_approved=True, privilege='M')

        # member attempts to change admin
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={'user_id': self.aristotle.user_id,
                                         'member_id': self.plato.user_id,
                                         'change_to': 'member'},
                                   content_type='application/json', HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(response.status_code, 401)

        # admin attempts to change owner
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={'user_id': self.plato.user_id,
                                         'member_id': self.socrates.user_id,
                                         'change_to': 'member'},
                                   content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 401)

        # admin attempts to appoint new admin
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={'user_id': self.plato.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'change_to': 'admin'},
                                   content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 401)

        # however, owner can do that
        response = self.client.put(f'/api/chat/{self.athens.chat_id}/management',
                                   data={'user_id': self.socrates.user_id,
                                         'member_id': self.aristotle.user_id,
                                         'change_to': 'admin'},
                                   content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)

    # === Chat detail ===
    def test_chat_detail_success(self):
        response = self.client.get(f'/api/chat/{self.athens.chat_id}/detail',
                                   content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['member_num'], 2)
        self.assertEqual(response.json()['chat_name'], 'Athens')
        self.assertEqual(response.json()['owner_id'], self.socrates.user_id)

    def test_chat_detail_fail(self):
        response = self.client.post(f'/api/chat/{self.athens.chat_id}/detail',
                                    content_type='application/json')
        self.assertEqual(response.status_code, 405)

        response = self.client.get(f'/api/chat/hello/detail',
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/api/chat/102909/detail',
                                   content_type='application/json')
        self.assertEqual(response.status_code, 404)

    # === get message list ===
    def test_get_message_list_success(self):
        socrates_token = self.client.post('/api/user/login',
                                          data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                          content_type='application/json').json()['token']

        plato_token = self.client.post('/api/user/login',
                                       data={'user_name': 'plato', 'password': 'plato_pwd'},
                                       content_type='application/json').json()['token']

        Message.objects.create(sender_id=self.socrates.user_id, chat_id=self.athens.chat_id,
                               msg_text='Message #1', msg_type='T', create_time=1000, update_time=1000)

        Message.objects.create(sender_id=self.plato.user_id, chat_id=self.athens.chat_id,
                               msg_text='Message 2', msg_type='T', create_time=2000, update_time=2000)

        Message.objects.create(sender_id=self.socrates.user_id, chat_id=self.athens.chat_id,
                               msg_text='Message #3', msg_type='T', create_time=3000, update_time=3000)

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'filter_after': 2500,
                                   }, HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['messages'][0]['msg_text'], 'Message #3')

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': self.plato.user_id,
                                       'filter_before': 1500,
                                       'filter_user': self.socrates.user_id
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['messages']), 1)

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': self.plato.user_id,
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['messages']), 3)

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': self.plato.user_id,
                                       'filter_text': 'Message #'
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['messages']), 2)

    def test_get_message_list_bad_request(self):
        plato_token = self.client.post('/api/user/login',
                                       data={'user_name': 'plato', 'password': 'plato_pwd'},
                                       content_type='application/json').json()['token']

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': 'hello'
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/api/chat/hello/messages',
                                   data={
                                       'user_id': self.plato.user_id,
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 400)

    def test_get_message_list_bad_method(self):
        plato_token = self.client.post('/api/user/login',
                                       data={'user_name': 'plato', 'password': 'plato_pwd'},
                                       content_type='application/json').json()['token']

        response = self.client.post(f'/api/chat/{self.athens.chat_id}/messages',
                                    data={
                                        'user_id': self.plato.user_id,
                                    }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 405)

        response = self.client.put(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': self.plato.user_id,
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 405)

        response = self.client.delete(f'/api/chat/{self.athens.chat_id}/messages',
                                      data={
                                          'user_id': self.plato.user_id,
                                      }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 405)

    def test_get_message_list_unauthorized(self):
        aristotle_token = self.client.post('/api/user/login',
                                           data={'user_name': 'aristotle', 'password': 'aristotle_pwd'},
                                           content_type='application/json').json()['token']

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': self.plato.user_id,
                                   }, HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(response.status_code, 401)

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': self.aristotle.user_id,
                                   }, HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(response.status_code, 401)

    def test_get_message_list_not_found(self):
        plato_token = self.client.post('/api/user/login',
                                       data={'user_name': 'plato', 'password': 'plato_pwd'},
                                       content_type='application/json').json()['token']

        response = self.client.get(f'/api/chat/102909/messages',
                                   data={
                                       'user_id': self.plato.user_id,
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f'/api/chat/{self.athens.chat_id}/messages',
                                   data={
                                       'user_id': 1283912,
                                   }, HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 404)
