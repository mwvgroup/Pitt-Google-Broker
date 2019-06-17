from google.cloud import pubsub_v1
import pickle


def publish_alerts(project_id, topic_name, alerts):
    
    publisher = pubsub_v1.PublisherClient()
    
    topic_path = publisher.topic_path(project_id, topic_name)
    
    for alert in alerts:
        
        alert.pop("cutoutScience")
        alert.pop("cutoutTemplate")
        alert.pop("cutoutDifference")
        
        pickled = pickle.dumps(alert)
    
        future = publisher.publish(topic_path, data=pickled)
    

# Create a user module for accessing those messages via a subscription

def subscribe_alerts(project_id, subscription_name, max_alerts=1):
    
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    
    response = subscriber.pull(subscription_path, max_messages=max_alerts)
    
    ack_ids = []
    for received_message in response.received_messages:
        ack_ids.append(received_message.ack_id)
    
    subscriber.acknowledge(subscription_path, ack_ids)
    
    return(response.received_messages)