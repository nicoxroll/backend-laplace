
import pika
import json
import logging
import os
from functools import wraps
import time

logger = logging.getLogger(__name__)

# Get RabbitMQ connection parameters from environment variables or use defaults
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', 5672))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'guest')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'guest')
RABBITMQ_VHOST = os.getenv('RABBITMQ_VHOST', '/')

def retry_on_connection_error(max_retries=5, delay=2):
    """
    Decorator to retry a function if a connection error occurs.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (pika.exceptions.AMQPConnectionError, 
                        pika.exceptions.ChannelClosedByBroker,
                        pika.exceptions.ConnectionClosedByBroker) as e:
                    logger.warning(f"Connection error: {e}, retrying in {delay} seconds...")
                    retries += 1
                    if retries < max_retries:
                        time.sleep(delay)
                    else:
                        logger.error(f"Failed after {max_retries} retries")
                        raise
        return wrapper
    return decorator

class RabbitMQClient:
    """
    A client for interacting with RabbitMQ.
    """
    def __init__(self, host=RABBITMQ_HOST, port=RABBITMQ_PORT, 
                 username=RABBITMQ_USER, password=RABBITMQ_PASS, 
                 virtual_host=RABBITMQ_VHOST):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.connection = None
        self.channel = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @retry_on_connection_error()
    def connect(self):
        """
        Establish a connection to RabbitMQ and create a channel.
        """
        if self.connection is not None and self.connection.is_open:
            return

        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
        return self.channel

    def close(self):
        """
        Close the channel and connection.
        """
        if self.channel is not None and self.channel.is_open:
            self.channel.close()
            
        if self.connection is not None and self.connection.is_open:
            self.connection.close()
            
        logger.info("Closed RabbitMQ connection")

    @retry_on_connection_error()
    def declare_queue(self, queue_name, durable=True, exclusive=False, auto_delete=False):
        """
        Declare a queue on RabbitMQ.
        """
        if self.channel is None or not self.channel.is_open:
            self.connect()
            
        self.channel.queue_declare(
            queue=queue_name, 
            durable=durable, 
            exclusive=exclusive, 
            auto_delete=auto_delete
        )
        logger.info(f"Declared queue: {queue_name}")

    @retry_on_connection_error()
    def declare_exchange(self, exchange_name, exchange_type='direct', durable=True, auto_delete=False):
        """
        Declare an exchange on RabbitMQ.
        """
        if self.channel is None or not self.channel.is_open:
            self.connect()
            
        self.channel.exchange_declare(
            exchange=exchange_name, 
            exchange_type=exchange_type,
            durable=durable,
            auto_delete=auto_delete
        )
        logger.info(f"Declared exchange: {exchange_name}")

    @retry_on_connection_error()
    def bind_queue(self, queue_name, exchange_name, routing_key=''):
        """
        Bind a queue to an exchange with a routing key.
        """
        if self.channel is None or not self.channel.is_open:
            self.connect()
            
        self.channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )
        logger.info(f"Bound queue {queue_name} to exchange {exchange_name} with routing key '{routing_key}'")

    @retry_on_connection_error()
    def publish(self, exchange_name, routing_key, message, properties=None):
        """
        Publish a message to an exchange.
        """
        if self.channel is None or not self.channel.is_open:
            self.connect()
        
        # Convert dict to json string if message is a dict
        if isinstance(message, dict):
            message = json.dumps(message)
            
        # Ensure message is bytes
        if isinstance(message, str):
            message = message.encode('utf-8')
            
        # Default properties if not provided
        if properties is None:
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
            
        self.channel.basic_publish(
            exchange=exchange_name,
            routing_key=routing_key,
            body=message,
            properties=properties
        )
        logger.debug(f"Published message to exchange {exchange_name} with routing key '{routing_key}'")

    @retry_on_connection_error()
    def consume(self, queue_name, callback, auto_ack=True, consumer_tag=None):
        """
        Start consuming messages from a queue.
        """
        if self.channel is None or not self.channel.is_open:
            self.connect()
            
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=callback,
            auto_ack=auto_ack,
            consumer_tag=consumer_tag
        )
        logger.info(f"Started consuming from queue: {queue_name}")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            logger.info("Consumer stopped by KeyboardInterrupt")

    def stop_consuming(self, consumer_tag=None):
        """
        Stop consuming messages.
        """
        if self.channel is not None and self.channel.is_open:
            if consumer_tag:
                self.channel.basic_cancel(consumer_tag)
            else:
                self.channel.stop_consuming()
            logger.info("Stopped consuming messages")

    @retry_on_connection_error()
    def get_message(self, queue_name, auto_ack=True):
        """
        Get a single message from a queue.
        """
        if self.channel is None or not self.channel.is_open:
            self.connect()
            
        method_frame, header_frame, body = self.channel.basic_get(
            queue=queue_name,
            auto_ack=auto_ack
        )
        
        if method_frame:
            try:
                message = json.loads(body.decode('utf-8'))
                return {
                    'message': message,
                    'delivery_tag': method_frame.delivery_tag
                }
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {
                    'message': body,
                    'delivery_tag': method_frame.delivery_tag
                }
        else:
            return None


# Helper functions for quick access
def get_rabbitmq_client():
    """
    Get a configured RabbitMQ client instance.
    """
    return RabbitMQClient()


def publish_message(exchange_name, routing_key, message):
    """
    Quick helper to publish a message.
    """
    with RabbitMQClient() as client:
        client.publish(exchange_name, routing_key, message)


def setup_rabbitmq(queues=None, exchanges=None, bindings=None):
    """
    Setup RabbitMQ queues, exchanges and bindings in one go.
    
    Example:
        setup_rabbitmq(
            queues=[
                {'name': 'my_queue', 'durable': True},
                {'name': 'another_queue', 'durable': True}
            ],
            exchanges=[
                {'name': 'my_exchange', 'type': 'direct'},
                {'name': 'another_exchange', 'type': 'topic'}
            ],
            bindings=[
                {'queue': 'my_queue', 'exchange': 'my_exchange', 'routing_key': 'my_key'},
                {'queue': 'another_queue', 'exchange': 'another_exchange', 'routing_key': '#'}
            ]
        )
    """
    with RabbitMQClient() as client:
        # Declare queues
        if queues:
            for queue in queues:
                client.declare_queue(
                    queue_name=queue['name'],
                    durable=queue.get('durable', True),
                    exclusive=queue.get('exclusive', False),
                    auto_delete=queue.get('auto_delete', False)
                )
        
        # Declare exchanges
        if exchanges:
            for exchange in exchanges:
                client.declare_exchange(
                    exchange_name=exchange['name'],
                    exchange_type=exchange.get('type', 'direct'),
                    durable=exchange.get('durable', True),
                    auto_delete=exchange.get('auto_delete', False)
                )
        
        # Create bindings
        if bindings:
            for binding in bindings:
                client.bind_queue(
                    queue_name=binding['queue'],
                    exchange_name=binding['exchange'],
                    routing_key=binding.get('routing_key', '')
                )
