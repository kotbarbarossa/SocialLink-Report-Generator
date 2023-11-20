import os
from dotenv import load_dotenv

load_dotenv()

kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
kafka_topic_consumer = os.getenv('KAFKA_TOPIC_CONSUMER')
# kafka_topic_producer = os.getenv('KAFKA_TOPIC_PRODUCER')
group_id = os.getenv('KAFKA_GROUP_ID')
