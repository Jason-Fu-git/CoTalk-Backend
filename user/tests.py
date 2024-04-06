from django.test import TestCase
from .models import User
from utils.utils_jwt import generate_jwt_token
from chat.models import Chat, Membership
import json


class UserTestCase(TestCase):

    def setUp(self):
        self.admin = User.objects.create(
            user_name='admin',
            password='admin_pwd',
            description='Administrator',
        )
        self.admin.save()
        self.guest = User.objects.create(
            user_name='guest',
            password='guest_pwd',
            user_email='guest@Athens.com',
        )
        self.guest.save()
        self.socrates = User.objects.create(
            user_name='Athens_socrates',
            password='socrates_pwd',
            description='A great philosopher'
        )
        self.socrates.save()
        self.plato = User.objects.create(
            user_name='Athens_plato',
            password='plato_pwd',
        )
        self.plato.save()
        self.aristotle = User.objects.create(
            user_name='Athens_aristotle',
            password='aristotle_pwd',
        )
        self.aristotle.save()

    # ! Util section
    def register(self, user_name, password, user_email=None, user_icon=None, description=None):
        body = {}
        if user_name is not None:
            body['user_name'] = user_name

        if password is not None:
            body['password'] = password

        if user_email is not None:
            body['user_email'] = user_email

        if user_icon is not None:
            body['user_icon'] = user_icon

        if description is not None:
            body['description'] = description

        return self.client.post('/api/user/register', data=body, content_type='application/json')

    def login(self, user_name, password):
        body = {}
        if user_name is not None:
            body['user_name'] = user_name

        if password is not None:
            body['password'] = password

        return self.client.post('/api/user/login', data=body, content_type='application/json')

    def update(self, user_id, token, user_name=None, password=None, user_email=None, user_icon=None, description=None):
        body = {}
        if user_name is not None:
            body['user_name'] = user_name

        if password is not None:
            body['password'] = password

        if user_email is not None:
            body['user_email'] = user_email

        if user_icon is not None:
            body['user_icon'] = user_icon

        if description is not None:
            body['description'] = description

        return self.client.put(f'/api/user/{user_id}', data=body, content_type='application/json',
                               HTTP_AUTHORIZATION=token)

    def delete(self, user_id, token):
        return self.client.delete(f'/api/user/{user_id}', content_type='application/json', HTTP_AUTHORIZATION=token)

    # ! Test section
    # === register section ===
    def test_register_success(self):
        response = self.register(user_name='test_register', password='test')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user_name'], 'test_register')
        response = self.register(user_name='test_register1', password='test', user_email='123@qq.com',
                                 description='Hello world')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user_email'], '123@qq.com')
        self.assertEqual(response.json()['description'], "Hello world")

    def test_register_fail_duplicate_user_name(self):
        self.register(user_name='test_conflict', password='test_conflict')
        response = self.register(user_name='test_conflict', password='test_conflict')
        self.assertEqual(response.status_code, 409)

    def test_register_fail_due_to_invalid_method(self):
        response1 = self.client.get('/api/user/register')
        self.assertEqual(response1.status_code, 405)
        response2 = self.client.delete('/api/user/register')
        self.assertEqual(response2.status_code, 405)
        response3 = self.client.put('/api/user/register')
        self.assertEqual(response3.status_code, 405)

    def test_register_fail_due_to_invalid_data(self):
        response1 = self.register(user_name=None, password=None, user_email=None, user_icon=None)
        self.assertEqual(response1.status_code, 400)
        response2 = self.register(user_name='', password='', user_email=None, user_icon=None)
        self.assertEqual(response2.status_code, 400)
        response3 = self.register(user_name='test', password=None, user_email='', user_icon=None)
        self.assertEqual(response3.status_code, 400)
        response4 = self.register(user_name='test', password='test', user_email='123@', user_icon=None)
        self.assertEqual(response4.status_code, 400)
        response5 = self.register(user_name='test', password='test', user_email='123@0900', user_icon=None)
        self.assertEqual(response5.status_code, 400)
        response6 = self.register(user_name='test', password='test', description="""
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            """)
        self.assertEqual(response6.status_code, 400)

    # === login section ===
    def test_login_success(self):
        response = self.login(user_name='admin', password='admin_pwd')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user_name'], 'admin')
        self.assertTrue(response.json()['token'])

    def test_login_user_not_found(self):
        response = self.login(user_name='admin1', password='admin_pwd')
        self.assertEqual(response.status_code, 404)

    def test_login_wrong_password(self):
        response = self.login(user_name='admin', password='admin_pwd1')
        self.assertEqual(response.status_code, 401)

    def test_login_invalid_parameters(self):
        response1 = self.login(user_name=None, password=None)
        self.assertEqual(response1.status_code, 400)
        response2 = self.login(user_name='admin', password=None)
        self.assertEqual(response2.status_code, 400)

    def test_login_wrong_methods(self):
        response1 = self.client.get('/api/user/login')
        self.assertEqual(response1.status_code, 405)
        response2 = self.client.delete('/api/user/login')
        self.assertEqual(response2.status_code, 405)
        response3 = self.client.put('/api/user/login')
        self.assertEqual(response3.status_code, 405)

    # === get section ===
    def test_get_success(self):
        response = self.client.get(f'/api/user/{self.guest.user_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user_id'], self.guest.user_id)
        self.assertEqual(response.json()['user_name'], self.guest.user_name)
        self.assertEqual(response.json()['user_email'], self.guest.user_email)

    def test_get_not_found(self):
        response = self.client.get(f'/api/user/{self.guest.user_id + 100000}')
        self.assertEqual(response.status_code, 404)

    def test_get_invalid_parameters(self):
        response2 = self.client.get('/api/user/hello')
        self.assertEqual(response2.status_code, 400)

    def test_get_invalid_methods(self):
        response1 = self.client.post('/api/user/1')
        self.assertEqual(response1.status_code, 405)

    # === update section ===
    def test_update_success(self):
        login_response = self.login(user_name='admin', password='admin_pwd')
        update_response = self.update(user_id=login_response.json()['user_id'],
                                      token=login_response.json()['token'],
                                      user_name='admin1', user_icon=None, password='admin1_pwd',
                                      user_email='123@qq.com', description='hello')
        self.assertEqual(update_response.status_code, 200)
        login_again_response = self.login(user_name='admin1', password='admin1_pwd')
        self.assertEqual(login_again_response.status_code, 200)
        self.assertEqual(login_again_response.json()['user_id'], login_response.json()['user_id'])
        self.assertEqual(login_again_response.json()['user_name'], 'admin1')
        self.assertEqual(login_again_response.json()['user_email'], '123@qq.com')
        self.assertEqual(login_again_response.json()['description'], 'hello')

    def test_update_wrong_token(self):
        login_admin = self.login(user_name='admin', password='admin_pwd')
        login_guest = self.login(user_name='guest', password='guest_pwd')
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=login_guest.json()['token'],
                               user_name='admin1', user_icon=None)
        self.assertEqual(response.status_code, 401)

    def test_update_wrong_user_id(self):
        response = self.update(user_id=1821838,
                               token=self.login(user_name='admin', password='admin_pwd').json()['token'],
                               user_name='admin1', user_icon=None)
        self.assertEqual(response.status_code, 404)

    def test_update_user_name_conflict(self):
        login_admin = self.login(user_name='admin', password='admin_pwd')
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=login_admin.json()['token'],
                               user_name='guest', user_icon=None)
        self.assertEqual(response.status_code, 409)

    def test_update_invalid_parameters(self):
        login_admin = self.login(user_name='admin', password='admin_pwd')
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=None,
                               user_name='admin1')
        self.assertEqual(response.status_code, 400)
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=login_admin.json()['token'],
                               user_name='')
        self.assertEqual(response.status_code, 400)
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=login_admin.json()['token'],
                               password='')
        self.assertEqual(response.status_code, 400)
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=login_admin.json()['token'],
                               user_email='123@')
        self.assertEqual(response.status_code, 400)
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=login_admin.json()['token'],
                               description='')
        self.assertEqual(response.status_code, 400)
        response = self.update(user_id=login_admin.json()['user_id'],
                               token=login_admin.json()['token'],
                               description="""
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            1234512345123451234512345123451234512345123451234512345123451234512345123451234512345\\
            """)
        self.assertEqual(response.status_code, 400)

    # === delete section ===
    def test_delete_success(self):
        register_delete = self.register(user_name='delete', password='delete_pwd')
        response = self.delete(user_id=register_delete.json()['user_id'],
                               token=register_delete.json()['token'])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(user_name='delete').exists())

    def test_delete_not_found(self):
        response = self.delete(user_id=100,
                               token=self.login(user_name='admin', password='admin_pwd').json()['token'])
        self.assertEqual(response.status_code, 404)

    def test_delete_not_authorized(self):
        response = self.delete(user_id=self.login(user_name='admin', password='admin_pwd').json()['user_id'],
                               token=self.login(user_name='guest', password='guest_pwd').json()['token'])
        self.assertEqual(response.status_code, 401)

    # === friend section ===
    def test_search_success(self):
        response = self.client.get(path='/api/user/search/Athens', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        users = response.json()['users']
        self.assertEqual(len(users), 4)
        have_entered = False
        for user in users:
            if user['user_id'] == self.socrates.user_id:
                self.assertEqual(user['description'], 'A great philosopher')
                have_entered = True
        response = self.client.get(path='/api/user/search')
        print(response.json())
        self.assertEqual(response.status_code, 200)
        users = response.json()['users']
        self.assertEqual(len(users), 5)

    def test_friend_request_success(self):
        plato_token = self.login(user_name='Athens_plato', password='plato_pwd').json()['token']
        socrates_token = self.login(user_name='Athens_socrates', password='socrates_pwd').json()['token']
        aristotle_token = self.login(user_name='Athens_aristotle', password='aristotle_pwd').json()['token']
        # socrates makes friend with plato
        self.client.put(path=f'/api/user/{self.socrates.user_id}/friends',
                        data={'friend_id': self.plato.user_id},
                        content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.client.put(path=f'/api/user/{self.plato.user_id}/friends',
                        data={'friend_id': self.socrates.user_id},
                        content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        # plato makes friend with aristotle
        self.client.put(path=f'/api/user/{self.plato.user_id}/friends',
                        data={'friend_id': self.aristotle.user_id},
                        content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.client.put(path=f'/api/user/{self.aristotle.user_id}/friends',
                        data={'friend_id': self.plato.user_id},
                        content_type='application/json', HTTP_AUTHORIZATION=aristotle_token)
        # plato has two friends
        response = self.client.get(path=f'/api/user/{self.plato.user_id}/friends',
                                   content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['friends']), 2)
        friends = response.json()['friends']
        have_entered = False
        for friend in friends:
            if friend['user_id'] == self.socrates.user_id:
                self.assertEqual(friend['description'], 'A great philosopher')
                have_entered = True
        self.assertTrue(have_entered)
        # plato breaks friendship with aristotle
        self.client.put(path=f'/api/user/{self.plato.user_id}/friends',
                        data={'friend_id': self.aristotle.user_id,
                              'approve': False},
                        content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(len(self.plato.get_friends()), 1)
        # aristotle tries to make friends with socrates
        self.client.put(path=f'/api/user/{self.aristotle.user_id}/friends',
                        data={'friend_id': self.socrates.user_id},
                        content_type='application/json', HTTP_AUTHORIZATION=aristotle_token)
        self.assertEqual(len(self.aristotle.get_friends()), 0)
        # however, socrates disapproves
        self.client.put(path=f'/api/user/{self.socrates.user_id}/friends',
                        data={'friend_id': self.aristotle.user_id,
                              'approve': False},
                        content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(len(self.aristotle.get_friends()), 0)
        self.assertEqual(len(self.socrates.get_friends()), 1)
        # test the corner case
        self.client.put(path=f'/api/user/{self.plato.user_id}/friends',
                        data={'friend_id': self.socrates.user_id},
                        content_type='application/json', HTTP_AUTHORIZATION=plato_token)
        self.assertEqual(len(self.plato.get_friends()), 1)
        self.client.put(path=f'/api/user/{self.aristotle.user_id}/friends',
                        data={'friend_id': self.socrates.user_id,
                              'approve': False},
                        content_type='application/json', HTTP_AUTHORIZATION=aristotle_token)
        self.client.put(path=f'/api/user/{self.socrates.user_id}/friends',
                        data={'friend_id': self.aristotle.user_id,
                              'approve': True},
                        content_type='application/json', HTTP_AUTHORIZATION=socrates_token)
        self.assertEqual(len(self.aristotle.get_friends()), 1)

    def test_friend_bad_method(self):
        response = self.client.post(f'/api/user/{self.guest.user_id}/friends')
        self.assertEqual(response.status_code, 405)
        response = self.client.delete(f'/api/user/{self.guest.user_id}/friends')
        self.assertEqual(response.status_code, 405)
        response = self.client.put(f'/api/user/search')
        self.assertEqual(response.status_code, 405)
        response = self.client.delete(f'/api/user/search')
        self.assertEqual(response.status_code, 405)
        response = self.client.post(f'/api/user/search/Ath')
        self.assertEqual(response.status_code, 405)

    def test_friend_unauthenticated(self):
        response = self.client.put(f'/api/user/{self.guest.user_id}/friends',
                                   data={'friend_id': self.aristotle.user_id},
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        response = self.client.get(f'/api/user/{self.guest.user_id}/friends',
                                   content_type='application/json')
        self.assertEqual(response.status_code, 400)
        admin_token = self.login(user_name='admin', password='admin_pwd').json()['token']
        response = self.client.get(f'/api/user/{self.guest.user_id}/friends',
                                   HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 401)

    def test_friend_not_found(self):
        response = self.client.put(f'/api/user/10000/friends')
        self.assertEqual(response.status_code, 404)
        response = self.client.get(f'/api/user/10000/friends')
        self.assertEqual(response.status_code, 404)
        admin_token = self.login(user_name='admin', password='admin_pwd').json()['token']
        response = self.client.put(f'/api/user/{self.admin.user_id}/friends',
                                   data={'friend_id': 10000},
                                   content_type='application/json',
                                   HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['info'], 'Invalid friend id')

    def test_friend_bad_request(self):
        guest_token = self.login(user_name='guest', password='guest_pwd').json()['token']
        response = self.client.put(f'/api/user/{self.guest.user_id}/friends',
                                   HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 400)
        response = self.client.put(path=f'/api/user/{self.guest.user_id}/friends',
                                   data={'friend_id': 'hello'},
                                   content_type='application/json', HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 400)
        response = self.client.put(path=f'/api/user/{self.guest.user_id}/friends',
                                   data={'friend_id': self.guest.user_id,
                                         'approve': 'OK'},
                                   content_type='application/json', HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 400)

    # === chat ===
    def test_get_chat_list_success(self):
        admin_response = self.login(user_name='admin', password='admin_pwd')
        admin_token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']

        chatA = Chat.objects.create(chat_name='Admin_chat')
        chatB = Chat.objects.create(chat_name='Empty_chat')
        chatA.save()
        chatB.save()

        membership = Membership.objects.create(user_id=admin_id, chat=chatA, is_approved=True)
        membership.save()

        response = self.client.get(path=f"/api/user/{admin_id}/chats", data={}, content_type='application/json',
                                   HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 200)
        chats = response.json()['chats']
        self.assertEqual(len(chats), 1)
        self.assertEqual(chats[0]['chat_name'], 'Admin_chat')

    def test_exit_chat_success(self):
        admin_response = self.login(user_name='admin', password='admin_pwd')
        admin_token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']

        guest_response = self.login(user_name='guest', password='guest_pwd')
        guest_token = guest_response.json()['token']
        guest_id = guest_response.json()['user_id']

        chatA = Chat.objects.create(chat_name='Admin_chat', is_private=False)
        chatA.save()

        admin_membership = Membership.objects.create(user_id=admin_id, chat=chatA, privilege='O', is_approved=True)
        admin_membership.save()

        guest_membership = Membership.objects.create(user_id=guest_id, chat=chatA, privilege='M',
                                                     is_approved=True)
        guest_membership.save()

        response = self.client.get(path=f"/api/user/{admin_id}/chats", data={}, content_type='application/json',
                                   HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 200)
        chats = response.json()['chats']
        self.assertEqual(len(chats), 1)
        self.assertEqual(chats[0]['chat_name'], 'Admin_chat')

        # admin exits
        response = self.client.delete(path=f"/api/user/{admin_id}/chats", data={"chat_id": chatA.chat_id},
                                      content_type='application/json', HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Membership.objects.filter(user_id=admin_id).exists())
        self.assertTrue(Membership.objects.get(user_id=guest_id).privilege == 'O')

        # guest exits
        response = self.client.delete(path=f"/api/user/{guest_id}/chats", data={"chat_id": chatA.chat_id},
                                      content_type='application/json', HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Chat.objects.filter(chat_name='Admin_chat').exists())

    def test_chat_management_bad_method(self):
        admin_response = self.login(user_name='admin', password='admin_pwd')
        admin_token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']

        chatA = Chat.objects.create(chat_name='Admin_chat')
        chatB = Chat.objects.create(chat_name='Empty_chat')
        chatA.save()
        chatB.save()

        membership = Membership.objects.create(user_id=admin_id, chat=chatA, is_approved=True)
        membership.save()

        response = self.client.put(path=f"/api/user/{admin_id}/chats", data={}, content_type='application/json',
                                   HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 405)

        response = self.client.post(path=f"/api/user/{admin_id}/chats", data={}, content_type='application/json',
                                    HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 405)

    def test_chat_management_bad_id(self):
        admin_response = self.login(user_name='admin', password='admin_pwd')
        admin_token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']

        chatA = Chat.objects.create(chat_name='Admin_chat')
        chatB = Chat.objects.create(chat_name='Empty_chat')
        chatA.save()
        chatB.save()

        membership = Membership.objects.create(user_id=admin_id, chat=chatA, is_approved=True)
        membership.save()

        response = self.client.get(path=f"/api/user/admin_id/chats", data={}, content_type='application/json',
                                   HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.delete(path=f"/api/user/{admin_id}/chats", data={},
                                      content_type='application/json', HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.delete(path=f"/api/user/{admin_id}/chats", data={"chat_id": "hello"},
                                      content_type='application/json', HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 400)

    def test_chat_management_unauthorized(self):
        admin_response = self.login(user_name='admin', password='admin_pwd')
        admin_token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']

        guest_response = self.login(user_name='guest', password='guest_pwd')
        guest_token = guest_response.json()['token']
        guest_id = guest_response.json()['user_id']

        response = self.client.get(path=f"/api/user/{admin_id}/chats", data={}, content_type='application/json',
                                   HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 401)

    def test_chat_management_not_found(self):
        admin_response = self.login(user_name='admin', password='admin_pwd')
        admin_token = admin_response.json()['token']
        admin_id = admin_response.json()['user_id']

        guest_response = self.login(user_name='guest', password='guest_pwd')
        guest_token = guest_response.json()['token']
        guest_id = guest_response.json()['user_id']

        chatA = Chat.objects.create(chat_name='Admin_chat', is_private=False)
        chatA.save()

        admin_membership = Membership.objects.create(user_id=admin_id, chat=chatA, privilege='O', is_approved=True)
        admin_membership.save()

        response = self.client.get(path=f"/api/user/{10000}/chats", data={}, content_type='application/json',
                                   HTTP_AUTHORIZATION=admin_token)
        self.assertEqual(response.status_code, 404)

        # guest exits
        response = self.client.delete(path=f"/api/user/{guest_id}/chats", data={"chat_id": chatA.chat_id},
                                      content_type='application/json', HTTP_AUTHORIZATION=guest_token)
        self.assertEqual(response.status_code, 404)
