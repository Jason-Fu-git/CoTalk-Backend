from django.test import TestCase
from user.models import User
from chat.models import Chat, Membership
from message.models import Message, Notification
from django.core.files.uploadedfile import SimpleUploadedFile
import os


class MessageTestCase(TestCase):
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
        self.admin = User.objects.create(
            user_name='admin',
            password='admin_pwd',
        )

        self.aristotle.save()
        self.athens = Chat.objects.create(
            chat_name='Athens',
            is_private=False
        )
        membership1 = Membership.objects.create(user_id=self.socrates.user_id, chat_id=self.athens.chat_id
                                                , is_approved=True, privilege='O')
        membership1.save()
        membership2 = Membership.objects.create(user_id=self.plato.user_id, chat_id=self.athens.chat_id,
                                                is_approved=True, privilege='A')
        membership2.save()
        membership3 = Membership.objects.create(user_id=self.aristotle.user_id, chat_id=self.athens.chat_id,
                                                is_approved=True, privilege='M')
        membership3.save()

        self.socrates_token = self.client.post('/api/user/login',
                                               data={'user_name': 'socrates', 'password': 'socrates_pwd'},
                                               content_type='application/json').json()['token']

        self.plato_token = self.client.post('/api/user/login',
                                            data={'user_name': 'plato', 'password': 'plato_pwd'},
                                            content_type='application/json').json()['token']
        self.admin_token = self.client.post('/api/user/login',
                                            data={'user_name': 'admin', 'password': 'admin_pwd'},
                                            content_type='application/json').json()['token']

    def tearDown(self):
        for filename in os.listdir('assets/message'):
            file_path = os.path.join('assets/message', filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Failed to delete file: {file_path}, Error: {e}")

    # === post message ===
    def test_post_message_success(self):
        # text
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(msg_id=response.json()['msg_id'])
        self.assertEqual(message.msg_text, 'Hello World!')

        # image
        with open('test_files/imagefile.png', 'rb') as f:
            image_file = SimpleUploadedFile(name='imagefile.png', content=f.read(), content_type='image/png')
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Image file',
                                        'msg_type': 'image',
                                        'msg_file': image_file,
                                    }, format='multipart',
                                    files={'msg_file': image_file},
                                    HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(msg_id=response.json()['msg_id'])
        self.assertTrue(message.msg_file.name.endswith('.png'))

        # audio
        with open('test_files/audiofile.mp3', 'rb') as f:
            audio_file = SimpleUploadedFile(name='audiofile.mp3', content=f.read(), content_type='audio/mp3')

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Audio file',
                                        'msg_type': 'audio',
                                        'msg_file': audio_file,
                                    }, format='multipart',
                                    files={'msg_file': audio_file},
                                    HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(msg_id=response.json()['msg_id'])
        self.assertTrue(message.msg_file.name.endswith('.mp3'))

        # video
        with open('test_files/videofile.mp4', 'rb') as f:
            video_file = SimpleUploadedFile(name='videofile.mp4', content=f.read(), content_type='video/mp4')

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Video file',
                                        'msg_type': 'video',
                                        'msg_file': video_file,
                                    }, format='multipart',
                                    files={'msg_file': video_file},
                                    HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(msg_id=response.json()['msg_id'])
        self.assertTrue(message.msg_file.name.endswith('.mp4'))

        # others
        with open('test_files/textfile.txt', 'rb') as f:
            text_file = SimpleUploadedFile(name='textfile.txt', content=f.read(),
                                           content_type='application/octet-stream')

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Text file',
                                        'msg_type': 'others',
                                        'msg_file': text_file,
                                    }, format='multipart',
                                    files={'msg_file': text_file},
                                    HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(msg_id=response.json()['msg_id'])
        self.assertTrue(message.msg_file.name.endswith('.txt'))

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                        'reply_to': message.msg_id,
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)

    def test_post_message_invalid_reply_to(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                        'reply_to': 'ni',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                        'reply_to': 10090,
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 404)

    def test_post_message_bad_request(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text':
                                            """
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            01234567890123456789012345678901234567890123456789
                                            """,
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!'
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'jsdilha',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        # others - image
        with open('test_files/textfile.txt', 'rb') as f:
            text_file = SimpleUploadedFile(name='textfile.txt', content=f.read(),
                                           content_type='application/octet-stream')

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'file',
                                        'msg_type': 'image',
                                        'msg_file': text_file,
                                    }, format='multipart',
                                    files={'msg_file': text_file},
                                    HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        # others - audio
        with open('test_files/textfile.txt', 'rb') as f:
            text_file = SimpleUploadedFile(name='textfile.txt', content=f.read(),
                                           content_type='application/octet-stream')

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'file',
                                        'msg_type': 'audio',
                                        'msg_file': text_file,
                                    }, format='multipart',
                                    files={'msg_file': text_file},
                                    HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

        # others - video
        with open('test_files/textfile.txt', 'rb') as f:
            text_file = SimpleUploadedFile(name='textfile.txt', content=f.read(),
                                           content_type='application/octet-stream')

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'file',
                                        'msg_type': 'video',
                                        'msg_file': text_file,
                                    }, format='multipart',
                                    files={'msg_file': text_file},
                                    HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 400)

    def test_post_message_bad_method(self):
        response = self.client.get('/api/message/send',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'chat_id': self.athens.chat_id,
                                       'msg_text': 'Hello World!',
                                       'msg_type': 'text',
                                   }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 405)

        response = self.client.put('/api/message/send',
                                   data={
                                       'user_id': self.socrates.user_id,
                                       'chat_id': self.athens.chat_id,
                                       'msg_text': 'Hello World!',
                                       'msg_type': 'text',
                                   }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 405)

        response = self.client.delete('/api/message/send',
                                      data={
                                          'user_id': self.socrates.user_id,
                                          'chat_id': self.athens.chat_id,
                                          'msg_text': 'Hello World!',
                                          'msg_type': 'text',
                                      }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)

        self.assertEqual(response.status_code, 405)

    def test_post_message_unauthorized(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.plato_token)

        self.assertEqual(response.status_code, 401)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.admin.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.admin_token)

        self.assertEqual(response.status_code, 401)

    def test_post_message_not_found(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': 812082,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.plato_token)

        self.assertEqual(response.status_code, 404)

        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.plato.user_id,
                                        'chat_id': 217319,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.plato_token)

        self.assertEqual(response.status_code, 404)

    # === get a message ===
    def test_get_message_success(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.get(f'/api/message/{msg_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                   }, HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['msg_text'], 'Hello World!')

    def test_get_message_bad_request(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.get(f'/api/message/hello/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                   }, HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 400)

        response = self.client.get(f'/api/message/{msg_id}/management',
                                   data={
                                   }, HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 400)

    def test_get_message_unauthorized(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.get(f'/api/message/{msg_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                   }, HTTP_AUTHORIZATION=self.admin_token)
        self.assertEqual(response.status_code, 401)

        response = self.client.get(f'/api/message/{msg_id}/management',
                                   data={
                                       'user_id': self.admin.user_id,
                                   }, HTTP_AUTHORIZATION=self.admin_token)
        self.assertEqual(response.status_code, 401)

    def test_get_message_not_found(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.get(f'/api/message/{123456789}/management',
                                   data={'user_id': self.socrates.user_id,
                                         }, HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f'/api/message/{msg_id}/management',
                                   data={'user_id': 128318293,
                                         }, HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 404)

    # === REMOVE A MESSAGE ===
    def test_remove_message_success(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.delete(f'/api/message/{msg_id}/management',
                                      data={
                                          'user_id': self.socrates.user_id,
                                          'is_remove': True
                                      },
                                      content_type='application/json',
                                      HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Message.objects.filter(msg_id=msg_id).exists())

    def test_remove_message_precondition_failed(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        message = Message.objects.get(msg_id=msg_id)
        message.create_time = 0
        message.save()

        response = self.client.delete(f'/api/message/{msg_id}/management',
                                      data={
                                          'user_id': self.socrates.user_id,
                                          'is_remove': True
                                      },
                                      content_type='application/json',
                                      HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 412)

    def test_remove_message_unauthorized(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.delete(f'/api/message/{msg_id}/management',
                                      data={
                                          'user_id': self.plato.user_id,
                                          'is_remove': True
                                      },
                                      content_type='application/json',
                                      HTTP_AUTHORIZATION=self.plato_token)
        self.assertEqual(response.status_code, 401)

    # === delete a message ===
    def test_delete_message_success(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.delete(f'/api/message/{msg_id}/management',
                                      data={
                                          'user_id': self.socrates.user_id,
                                          'is_remove': False
                                      },
                                      content_type='application/json',
                                      HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Message.objects.filter(msg_id=msg_id).exists())

        response = self.client.get(f'/api/message/{msg_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                   },
                                   content_type='application/json',
                                   HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 401)

        # plato can see it, while socrates cannot
        plato_messages = self.athens.get_messages(unable_to_see_user_id=self.plato.user_id)
        socrates_messages = self.athens.get_messages(unable_to_see_user_id=self.socrates.user_id)

        self.assertEqual(len(plato_messages), 1)
        self.assertEqual(len(socrates_messages), 0)

    # === read a message ===
    def test_read_message_success(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.put(f'/api/message/{msg_id}/management',
                                   data={
                                       'user_id': self.socrates.user_id,
                                   },
                                   content_type='application/json',
                                   HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)

        response = self.client.put(f'/api/message/{msg_id}/management',
                                   data={
                                       'user_id': self.plato.user_id,
                                   },
                                   content_type='application/json',
                                   HTTP_AUTHORIZATION=self.plato_token)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f'/api/message/{msg_id}/management',
                                   data={
                                       'user_id': self.plato.user_id,
                                   },
                                   content_type='application/json',
                                   HTTP_AUTHORIZATION=self.plato_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['read_users']), 2)

    def test_read_message_bad_method(self):
        response = self.client.post('/api/message/send',
                                    data={
                                        'user_id': self.socrates.user_id,
                                        'chat_id': self.athens.chat_id,
                                        'msg_text': 'Hello World!',
                                        'msg_type': 'text',
                                    }, format='multipart', HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 200)
        msg_id = response.json()['msg_id']

        response = self.client.post(f'/api/message/{msg_id}/management',
                                    data={
                                        'user_id': self.socrates.user_id,
                                    },
                                    content_type='application/json',
                                    HTTP_AUTHORIZATION=self.socrates_token)
        self.assertEqual(response.status_code, 405)
