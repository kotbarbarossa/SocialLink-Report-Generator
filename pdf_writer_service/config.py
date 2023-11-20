import os
from dotenv import load_dotenv

load_dotenv()

kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
kafka_topic_consumer = os.getenv('KAFKA_TOPIC_CONSUMER')
group_id = os.getenv('KAFKA_GROUP_ID')
