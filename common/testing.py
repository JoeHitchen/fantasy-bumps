from django.contrib import messages


class MessagesTestMixin():
    
    levels_matrix = {10: 'debug', 20: 'info', 25: 'success', 30: 'warning', 40: 'error'}
        
    @classmethod
    def message_tuple(cls, msg):
        """Converts a message object into a tuple for easy comparison."""
        return (cls.levels_matrix[msg.level], msg.message)
    
    
    def assertMessages(self, response, expected):
        
        sent = [msg for msg in messages.get_messages(response.wsgi_request)]
        self.assertEqual(len(sent), len(expected))
        
        for i, msg in enumerate(expected):
            with self.subTest(index = i):
                self.assertEqual(self.message_tuple(sent[i]), msg)

