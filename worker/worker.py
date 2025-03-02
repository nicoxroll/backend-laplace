import pika
import json
import time
import logging
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flag to control graceful shutdown
should_continue = True

def process_task(ch, method, properties, body):
    """Process incoming analysis tasks."""
    try:
        data = json.loads(body)
        logger.info(f"Processing task: {data['query']}")
        
        # Actual processing logic would go here
        # For example:
        # result = analyze_query(data['query'])
        
        # Acknowledge message only after successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Task processed successfully")
    except Exception as e:
        logger.error(f"Error processing task: {str(e)}")
        # Negative acknowledgment to requeue the message in case of failure
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def connect_to_rabbitmq():
    """Establish connection to RabbitMQ with retry mechanism."""
    connection_params = "amqp://admin:securepass123@rabbitmq"
    
    while should_continue:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(connection_params))
            return connection
        except pika.exceptions.AMQPConnectionError:
            logger.warning("Failed to connect to RabbitMQ. Retrying in 5 seconds...")
            time.sleep(5)
    
    return None

def signal_handler(sig, frame):
    """Handle graceful shutdown on signals."""
    global should_continue
    logger.info("Shutdown signal received, stopping worker...")
    should_continue = False

def main():
    """Main worker function."""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        connection = connect_to_rabbitmq()
        if not connection:
            logger.error("Could not establish connection to RabbitMQ")
            return
        
        channel = connection.channel()
        channel.queue_declare(queue='analysis_tasks')
        
        # Configure QoS to limit messages per worker
        channel.basic_qos(prefetch_count=1)
        
        # Use manual acknowledgment
        channel.basic_consume(
            queue='analysis_tasks',
            on_message_callback=process_task,
            auto_ack=False)
        
        logger.info("Worker started. Waiting for messages...")
        
        while should_continue:
            connection.process_data_events(time_limit=1.0)
            
    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
    finally:
        if 'connection' in locals() and connection.is_open:
            connection.close()
            logger.info("Connection closed")

if __name__ == "__main__":
    main()
