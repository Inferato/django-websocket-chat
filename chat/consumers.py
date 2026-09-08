import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from .models import ChatMessage
from datetime import datetime


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Підключення до WebSocket"""
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        # Перевірка автентифікації
        if not self.user.is_authenticated:
            await self.close()
            return

        # Приєднання до групи
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Повідомляємо групі про підключення користувача
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'message': f'{self.user.username} приєднався до чату',
                'username': self.user.username,
                'status': 'online'
            }
        )

    async def disconnect(self, close_code):
        """Відключення від WebSocket"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'message': f'{self.user.username} вийшов з чату',
                'username': self.user.username,
                'status': 'offline'
            }
        )

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Отримання повідомлення від клієнта"""
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            message_type = data.get('type', 'message')

            if not message:
                return

            # Зберігаємо повідомлення в базу даних
            saved_message = await self.save_message(message)

            # Відправляємо повідомлення всім в групі
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': self.user.username,
                    'user_id': self.user.id,
                    'timestamp': saved_message['timestamp'],
                    'message_id': saved_message['id']
                }
            )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Невірний формат JSON'
            }))

    async def chat_message(self, event):
        """Обробка повідомлення чату"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
            'is_own': event['user_id'] == self.user.id
        }))

    async def user_status(self, event):
        """Обробка статусу користувача"""
        await self.send(text_data=json.dumps({
            'type': 'status',
            'message': event['message'],
            'username': event['username'],
            'status': event['status']
        }))

    @database_sync_to_async
    def save_message(self, message):
        """Збереження повідомлення в БД"""
        chat_message = ChatMessage.objects.create(
            room=self.room_name,
            user=self.user,
            content=message,
            timestamp=datetime.now()
        )
        return {
            'id': chat_message.id,
            'timestamp': chat_message.timestamp.isoformat()
        }
