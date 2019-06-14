from google.cloud import pubsub_v1



# Access ZTF alerts from the alert_acquistion module

# Convert those alerts into encoded packets that are then published

def publish_alerts(project_id, topic_name, alerts):
    
    publisher = pubsub_v1.PublisherClient()
    
    topic_path = publisher.topic_path(project_id, topic_name)
    
    data = # this comes from the alerts
    data = data.encode('utf-8')
    
    future = publisher.publish(topic_path, data=data)
    

# Create a user module for accessing those messages via a subscription

def subscribe_alerts(project_id, subscription_name, max_alerts=1):
    
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    
    response = subscriber.pull(subscription_path, max_messages=max_alerts)
    
    ack_ids = []
    for received_message in response.received_messages:
        ack_ids.append(received_message.ack_id)
    
    subscriber.acknowledge(subscription_path, ack_ids)