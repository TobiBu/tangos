import contextlib

class MessageMetaClass(type):
    _message_classes = {}

    def __new__(meta, name, bases, dct):
        return super(MessageMetaClass, meta).__new__(meta, name, bases, dct)

    def __init__(cls, name, bases, dct):
        super(MessageMetaClass, cls).__init__(name, bases, dct)
        MessageMetaClass.register_class(cls)

    @staticmethod
    def class_to_hash(cls):
        return hash(cls.__name__) & 0xfffffff

    @staticmethod
    def hash_to_class(hash):
        if hash not in MessageMetaClass._message_classes:
            raise RuntimeError, "Unknown message receieved"

        return MessageMetaClass._message_classes[hash]

    @staticmethod
    def class_is_known(cls):
        return MessageMetaClass.class_to_hash(cls) in MessageMetaClass._message_classes

    @staticmethod
    def register_class(cls):
        if MessageMetaClass.class_is_known(cls):
            raise AttributeError, "Attempting to register duplicate message class"
        MessageMetaClass._message_classes[MessageMetaClass.class_to_hash(cls)] = cls
        cls._tag = MessageMetaClass.class_to_hash(cls)


class Message(object):
    __metaclass__ = MessageMetaClass
    _handler = None

    def __init__(self, contents=None):
        self.contents = contents

    @classmethod
    def deserialize(cls, message):
        return cls(message)

    def serialize(self):
        return self.contents

    @staticmethod
    def interpret_and_deserialize(tag, source, message):
        obj = MessageMetaClass.hash_to_class(tag)(message)
        obj.source = source
        return obj

    @staticmethod
    def process_incoming_message(tag, source, message):
        obj = Message.interpret_and_deserialize(tag, source, message)
        obj.process()

    def send(self, destination):
        from . import backend
        backend.send(self.serialize(), destination=destination, tag=self._tag)

    @classmethod
    def receive(cls, source=None):
        from . import backend
        if cls is Message:
            msg, source, tag = backend.receive_any(source=None)
            obj = Message.interpret_and_deserialize(tag, source, msg)
        else:
            message = backend.receive(source, tag=cls._tag)
            obj = cls.deserialize(message)
            obj.source = source
        return obj

    def process(self):
        if self.__class__._handler:
            self.__class__._handler(self)
        else:
            raise RuntimeError, "Unable to dispatch message %s as no handler is registered"%self.__class__

    @classmethod
    def register_handler(cls, fn):
        if cls._handler is None:
            cls._handler = fn
        else:
            raise RuntimeError, "A handler is already registered for this message"

    @classmethod
    def unregister_handler(cls, fn):
        assert cls._handler is fn
        cls._handler = None
