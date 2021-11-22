# Pub/Sub Step-by-Step (note: _not_ a tutorial to pub\_sub\_client)

## Initial Setup

You'll need to install some additional requirements to use Pub/Sub. The main requirement is the `pubsub_v1` package, installable via

``` bash
pip install google-cloud-pubsub
```
If you want to use the gcloud commands listed below *without* accessing the Google Cloud Platform webpage online, you'll need to install gcloud via this webpage: https://cloud.google.com/sdk/. Otherwise, you can use the Python-based commands instead.

Create a project in Google Cloud Platform after starting the $300 trial. **Take note of the project number.**

You'll need to activate your APIs/Services and get an authentication JSON file:

- Go to the **Navigation menu** (top left) and click, going down to **APIs and Services** and clicking--this will take you to the the *Dashboard* page.
- Along the bottom, you should see a list of APIs.
- Click on **Cloud Pub/Sub API** to access the *Overview* page for this API and then click on **Credentials** along the left side of the screen.
- Click **CREATE CREDENTIALS** along the top and select **Service account key** as your option.
- If you haven't created a service account, you'll need to select **New service account** and fill in the relevant information.

> Note: I used "Role > Project > Owner" to get "full permissions", but this may not be the best option in the future. Recently, I tried "Pub/Sub > Pub/Sub Editor" with equally good results for the service account. This allows them to "Modify topics and subscriptions, publish and consume messages."

> Note: The service account has an associated "name", of sorts, that follows an email address format. It goes: `SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com`, where you set the SERVICE\_ACCOUNT\_NAME and the PROJECT\_ID is listed in the JSON file. The PROJECT\_ID is not the same as the project number. This email address is also listed in the JSON file as "client\_email".

- Then, make sure the *JSON* bullet option is still selected and click **Create**. This will create a JSON authentication file and download it to your computer.
- Locate this file, rename it however you see fit, and move it wherever you like, though do take note of this file path. Add a line in your .bash_profile file and restart your terminal session: 

``` bash
export GOOGLE_APPLICATION_CREDENTIALS="FILE_PATH/FILE_NAME.json"
```
	
- To check if this variable was set correctly, type `echo $GOOGLE_APPLICATION_CREDENTIALS` in your terminal to see if the correct file path is displayed. If so, you should be authenticated to use GCP from your current terminal session.
- You should also see the service account key listed on the *Credentials* page, and there is a trashcan icon on the right in case you need to delete these authentication credentials. *Note: doing so will make the JSON file useless.*

## Topics and Subscriptions
### Starting a Topic

By python script:
``` python
from google.cloud import pubsub_v1

project_id = 1111111111111	# replace with your project number
topic_name = my_topic	# replace with your topic name

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)
topic = publisher.create_topic(topic_path)

```

By GCP GUI:

- Click on the **Navigation menu** and scroll down and click on **Pub/Sub** under Big Data.
- This will take you to the *Topics* page, where you should see a **+ Create Topic button** along the top. Click on it and type in a name for your topic, clicking **Create** when you're done.

By GCP Console Commands:

```
gcloud pubsub topics create my_topic
```
> Note: It may take a few seconds for the topic to appear on your project's *Topics* page, so be patient.

### Starting a Subscription

By python script:
``` python
from google.cloud import pubsub_v1

project_id = 1111111111111	# replace with your project number
subscription_name = my_sub	# replace with your subscription name

subscriber = pubsub_v1.SubscriberClient()
topic_path = subscriber.topic_path(project_id, topic_name)
subscription_path = subscriber.subscription_path(project_id, subscription_name)

subscription = subscriber.create_subscription(subscription_path, topic_path)
```

By GCP GUI:

- Once the topic is available, **click on it** and then **CREATE SUBSCRIPTION** in the upper right. Here, you can enter a name for the subscription and change any of the settings.
- Once you're done, click **Create**.

By GCP Console Commands:

```
gcloud pubsub subscriptions create my-sub --topic my-topic
```

You can set the acknowledgment deadline time *#* (in seconds) using the option `--ack-deadline=#` at the end of the line above.

> Note: It may take a few seconds for the subscription to appear on your project's *Subscriptions* page, so be patient.

### Setting Permissions for Local Work

To publish and retrieve messages from Python scripts on your laptop, the permissions need to be slightly altered on the topic and subscription (I'm still not sure why).

- On your project's *Topics* page, select your topic's checkbox, which should make a new *Info Panel* appear on the right. If it doesn't appear, select **SHOW INFO PANEL** along the top right corner to un-hide it.
- Under the *PERMISSIONS* tab, you should see an **Owner drop-down box**. Clicking on it should reveal the two owners of this topic--the Google account you signed in as, and your service account email address.

> Note: While it will say the service account's ownership was inherited, this will not keep Google happy when it comes time to doing things with local Python scripts, or it didn't for me, anyway.

- Select **Add member** and paste the service account's email address (see the Note in *Initial Setup*) in the **New members box**.
- Since it inherited ownership, it should appear in a drop-down list below the *Add member* box; selecting the first entry worked for me, but the second may as well, I'm not sure.
- Select the same "Role > Project > Owner" and click **Save**. You'll notice that under the *inherited* column, the service account will now say **mixed**.

Repeat for the subscriptions you'd like to use, where the only change is in selecting the subscriptions by checkbox from your project's *Subscriptions* page. 

### Publishing and Retrieving Messages

Some of the code below is largely taken from [this quickstart guide](https://cloud.google.com/pubsub/docs/quickstart-client-libraries?refresh=1&pli=1#pubsub-quickstart-publish-python), and here is the guide for using [gcloud command-line tool](https://cloud.google.com/pubsub/docs/quickstart-cli?refresh=1).

#### Publishing

Via python script, assuming the topic has already been made:

``` python
from google.cloud import pubsub_v1

project_id = 1111111111111	# replace with your project number
topic_name = my_topic	# replace with your topic name

publisher = pubsub_v1.PublisherClient()

# The `topic_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/topics/{topic_name}`

topic_path = publisher.topic_path(project_id, topic_name)

for n in range(1, 4):
    data = u'Message number {}'.format(n)
    # Data must be a bytestring
    data = data.encode('utf-8')
    # When you publish a message, the client returns a future.
    future = publisher.publish(topic_path, data=data)
    print('Published {} of message ID {}.'.format(data, future.result()))

print('Published messages.')

```

Via GCP Console Commands:

```
 gcloud pubsub topics publish my-topic --message hello
 ```

#### Retrieve/Pull Messages

Via python script, assuming the subscription has already been made:

``` python
from google.cloud import pubsub_v1

project_id = 1111111111111	# replace with your project number
subscription_name = my_sub	# replace with your subscription name

subscriber = pubsub_v1.SubscriberClient()
# The `subscription_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/subscriptions/{subscription_name}`
subscription_path = subscriber.subscription_path(project_id, subscription_name)

max_messages = 10
response = subscriber.pull(subscription_path, max_messages=max_messages)

ack_ids = []
for received_message in response.received_messages:
    print("Received: {}".format(received_message.message.data))
    ack_ids.append(received_message.ack_id)

# Acknowledges the received messages so they will not be sent again.
subscriber.acknowledge(subscription_path, ack_ids)

print("Received and acknowledged {} messages. Done.".format(len(ack_ids)))
```
Via GCP Console Commands:

```
 gcloud pubsub subscriptions pull --auto-ack my-sub
 ```
The keyword `--limit=#` can be added between `--auto-ack` and `my_sub` to limit the number of messages you pull.

## Ordering Messages
Pub/Sub attempts to deliver a message to a subscriber once and in order, but this cannot be guaranteed. A new feature called **message ordering** has been implemented to help resolve this issue, with documentation on [publishing](https://cloud.google.com/pubsub/docs/publisher#using_ordering_keys) and more general info [here](https://cloud.google.com/pubsub/docs/ordering). Unfortunately, this is in beta for a handful of the APIs and in a closed alpha for others, including python (as of 8/6/2020). Updating your install of `google-cloud-pubsub` to the lastest version (8/62020: 1.7.0) will download code that has support for the new keyword, but it will not allow you to use the keyword when publishing. The following instructions are for future reference when these features become available, either in beta or through general availability.

First, enable message ordering for the subscription.

By GCP GUI: 

- When creating the subscription, select the checkbox to enable message ordering.
- Edit an existing subscription's settings and check the box to enable message ordering.

By GCP Console Commands:

```
gcloud beta pubsub subscriptions create my-sub --topic my-topic --enable-message-ordering
```

Then, when publishing a message, include a `message_ordering` keyword to your `publisher.publish` call. This should be a string. All messages that have the same `message_ordering` argument will then be compared by date, and the oldest messages among that group will be sent first.
> Note: Pub/Sub will only compare messages that have the *same* argument for the `message_ordering` keyword. It will also preferentially send the **oldest** messages among those it compares!
The addition of the keyword should look something like this:
``` python
publisher.publish(topic_path, data=data, message_ordering='orderstring')
```
