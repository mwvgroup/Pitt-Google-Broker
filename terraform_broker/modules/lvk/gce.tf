resource "google_compute_instance" "consumer_vm" {
  name         = "lvk-consumer"
  machine_type = "e2-custom-1-5632"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "family/debian-12"
    }
  }

  metadata = {
    google-logging-enabled = true
    startup-script-url = join("/", [
      "gs:",
      "",
      google_storage_bucket.broker_bucket.name,
      "lsst",
      "vm_install.sh"])
    shutdown-script-url=join("/", [
      "gs:",
      "",
      google_storage_bucket.broker_bucket.name,
      "lsst",
      "vm_shutdown.sh"])
  }

  network_interface {
    network = "default"
  }
}
