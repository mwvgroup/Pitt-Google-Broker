# Night conductor configuration

# Scheduling portion
# This consists of two schedule jobs, one for START and STOP.
# They publis to the ztk-cue_night_conductor topic.
resource "google_pubsub_topic" "night_conductor_topic" {
  name = "ztk-cue_night_conductor${local.dashed_test_suffix}"
}
resource "google_cloud_scheduler_job" "start_night_conductor" {
  name        = "ztf-cue_night_conductor_START${local.dashed_test_suffix}"
  description = "Night Conductor START signal"
  schedule    = "00 2 * * *"  # START at 2:00am UTC / 6:00pm PDT, everyday
  time_zone   = "UTC"

  pubsub_target {
    # topic.id is the topic's full resource name.
    topic_name = google_pubsub_topic.night_conductor_topic.id
    data = "START"
  }
}
resource "google_cloud_scheduler_job" "end_night_conductor" {
  name        = "ztf-cue_night_conductor_END${local.dashed_test_suffix}"
  description = "Night Conductor END signal"
  schedule    = "00 2 * * *"  # END at 2:00am UTC / 6:00pm PDT, everyday
  time_zone   = "UTC"

  pubsub_target {
    # topic.id is the topic's full resource name.
    topic_name = google_pubsub_topic.night_conductor_topic.id
    data = "END"
  }
}

# The night conductor itself is a VM.
google_compute_resource_policy "night_conductor" {
  name   = "ztf-night-conductor-schedule"
  region = var.region
  description = "Start Night Conductor VM each morning"
  snapshot_schedule_policy {
    schedule {
      vm_start_schedule {
	schedule = "00 16 * * *"  # 4:00pm UTC / 9:00am PDT, everyday
      }
      time_zone = "UTC"
    }
  }
}
resource "google_compute_instance" "consumer_vm" {
  name         = "ztf-night-conductor${dashed_test_suffix}"
  machine_type = "e2-standard-2"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "family/debian-12"
    }
  }

  metadata = {
    google-logging-enabled = true
    startup-script-url = "${google_storage_bucket.broker_bucket.url}/night_conductor/vm_install.sh"
  }

  network_interface {
    network = "default"
  }

  resource_policies = [
    google_compute_resource_policy.night_conductor.self_link
  ]
}
