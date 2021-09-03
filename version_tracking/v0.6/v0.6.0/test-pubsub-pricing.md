# Testing Pub/Sub tutorial from external account.

## Summary:

Date of tests: 8/6/2021 (note there were no live ZTF streams Aug 5-7)

ardent-cycling-243415 account:

- Pub/Sub billing charges look as expected.
- Charges for VM in Germany look as expected.
- All ingress/egress fees are $0.00

my-pgb-project-3 account:

I pulled and processed ~375000 messages with an average of 70607 bytes =~ 26.5 GB of data.
This should have been >2x the data allowed in the Free Tier.
I don't know why it didn't cut me off.
I successfully pulled all this stuff from a VM in Germany with no egress restrictions/fees.

There is no way for this account to be charged.
Billing is disabled and I have never created a billing account.
I can't even see a billing report because I don't have a billing account.

## Initial thoughts:

- Testing pricing, free tier, egress, msg delivery
- What happens if you don't enable billing and reach the Free Tier limit?
- Does "message delivery" mean delivered to the subscription or delivered to the user (on pull request)?
    - Note on [Pub/Sub pricing page](https://cloud.google.com/pubsub/pricing#pubsub) it says: "Storage of unacknowledged messages does not result in fees."

## Outline:

- streamed ~300,000 messages to the subscription projects/my-pgb-project-3/subscriptions/test
- setup a compute engine in Germany to pull the messages
    - compute engine is in pgb project since can't do VMs with free accounts. setup credentials to project my-pgb-project-3 following [v0.5.0/external-connection.md](../v0.5.0/external-connection.md)
- pulled the messages from the test subscription and wrote a sampling of message sizes to file

## Code to do it:

Use the stream-looper VM to publish the messages.

Setup VM to pull from my-pgb-project-3:

```bash
vmname=pubsub-test
zone=europe-west3-a  # Frankfurt, Germany
machinetype="e2-standard-2"
gcloud compute instances create "$vmname" \
    --zone="$zone" \
    --machine-type="$machinetype" \
    --scopes=cloud-platform

gcloud compute ssh $vmname --zone $zone

sudo apt-get update
sudo apt-get install -y python3-pip screen ipython3
sudo pip3 install pgb-utils
```

Pull and process messages:

```python
import pgb_utils as pgb
import random

def callback(message):
    # save some stuff from a sampling of messages
    n = random.uniform(0,1)
    if n > 0.99:
        try:
            fout = 'track-msgs.txt'
            with open(fout, 'a') as f:
                f.write(f'{message.size}\n')
        except:
            pass
    # acknowledge
    message.ack()

sub_name = 'test'
pgb.pubsub.streamingPull(sub_name, callback, timeout=None)
```
