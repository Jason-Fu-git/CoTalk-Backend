from django.test import TestCase
from .models import User
from utils.utils_jwt import generate_jwt_token


class UserTestCase(TestCase):

    def setUp(self):
        admin = User.objects.create(
            user_name='admin',
            password='admin_pwd',
        )
        admin.save()
        guest = User.objects.create(
            user_name='guest',
            password='guest_pwd',
        )
        guest.save()

    # ! Util section
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

        return self.client.post('/api/user/register', data=body, content_type='application/json')

    def login(self, user_name, password):
        body = {}
        if user_name is not None:
            body['user_name'] = user_name

        if password is not None:
            body['password'] = password

        return self.client.post('/api/user/login', data=body, content_type='application/json')

    def update(self, user_id, token, user_name=None, password=None, user_email=None, user_icon=None):
        body = {}
        if user_name is not None:
            body['user_name'] = user_name

        if password is not None:
            body['password'] = password

        if user_email is not None:
            body['user_email'] = user_email

        if user_icon is not None:
            body['user_icon'] = user_icon

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
        response = self.register(user_name='test_register1', password='test', user_email='123@qq.com')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user_email'], '123@qq.com')

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

    # === update section ===
    def test_update_success(self):
        login_response = self.login(user_name='admin', password='admin_pwd')
        update_response = self.update(user_id=login_response.json()['user_id'],
                                      token=login_response.json()['token'],
                                      user_name='admin1', user_icon=None)
        self.assertEqual(update_response.status_code, 200)
        login_again_response = self.login(user_name='admin1', password='admin_pwd')
        self.assertEqual(login_again_response.status_code, 200)
        self.update(user_id=login_response.json()['user_id'],
                    token=login_response.json()['token'],
                    user_name='admin')

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
