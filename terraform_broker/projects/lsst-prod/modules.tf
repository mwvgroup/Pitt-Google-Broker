module "lsst" {
  src = "../brokers/lsst"

  project {
    id = ""  # TODO
    number = 0  # TODO
    region = "us-central1"
    zone = "us-central1-a"
    owners = []  # TODO
    editors = []  # TODO
    viewers = [
      "astro@pingenot.org",
    ]
  }
  environment = {
    prod = true
  }
}


module "upsilon_classifer" {
  source = "../classifiers/upsilon"

  dataset_id = lsst.dataset_id
  pubsub_topic = lsst.pubsub_topic
}
