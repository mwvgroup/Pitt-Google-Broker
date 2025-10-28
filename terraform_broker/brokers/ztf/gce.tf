local {
  consumer_use_authentication_string = tostring(var.use_authentication)
}

google_compute_resource_policy "consumer_vm_policy" {
  name   = "ztf-consumer-schedule${local.dashed_test_suffix}"
  region = var.region
  description = "Start consumer VM each night, stop each morning."
  snapshot_schedule_policy {
    schedule {
      vm_start_schedule {
	schedule = "30 1 * * *"  # 1:30am UTC / 5:30pm PDT, everyday
      }
      vm_start_schedule {
	schedule = "55 13 * * *"  # 1:55pm UTC / 6:55am PDT, everyday
      }
      time_zone = "UTC"
    }
  }
}

    gcloud compute firewall-rules create 'ztfport' \
        --allow=tcp:9094 \
        --description=
        --direction=INGRESS \
        --enable-logging
	google_compute_firewall "ztfport" {
	  name = "ztfport"
  description = "Allow incoming traffic on TCP port 9094"
}

resource "google_compute_instance" "consumer_vm" {
  name         = "ztf-consumer"
  machine_type = "e2-standard-2"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "family/debian-12"
    }
  }

  metadata = {
    google-logging-enabled = true
    startup-script-url = "${google_storage_bucket.broker_bucket.url}/ztf/vm_install.sh"
    shutdown-script-url = "${google_storage_bucket.broker_bucket.url}/ztf/vm_shutdown.sh"
    "USE_AUTHENTICATION=${local.consumer_use_authentication_string}"
  }

  network_interface {
    network = "default"
  }

  tags = ["ztfport"]

  resource_policies = [
    google_compute_resource_policy.consumer_vm.self_link
  ]
}
