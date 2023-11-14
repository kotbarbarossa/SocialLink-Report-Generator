import os
from dotenv import load_dotenv

load_dotenv()

kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
kafka_topic_vk = os.getenv('KAFKA_TOPIC_VK')
kafka_topic_instagram = os.getenv('KAFKA_TOPIC_INSTAGRAM')
kafka_topic_telegram = os.getenv('KAFKA_TOPIC_TELEGRAM')
group_id = os.getenv('KAFKA_GROUP_ID')
