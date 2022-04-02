resource "google_pubsub_topic" "exgalac_trans" {
  name    = "ztf-exgalac_trans-${var.suffix}"
  project = var.project
}

resource "google_pubsub_topic_iam_member" "publisher" {
  topic      = google_pubsub_topic.exgalac_trans.name
  role       = "projects/sen-pittitops-komprise/roles/pubsub.topics.attachSubscription"
  member     = "allUsers"
  project    = google_pubsub_topic.exgalac_trans.project
  depends_on = [google_pubsub_topic.exgalac_trans]
}

output "topic_name" {
  value       = google_pubsub_topic.exgalac_trans.name
  description = "Name of the created pub/sub topic"
}
