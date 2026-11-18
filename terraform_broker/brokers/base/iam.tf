resource google_project_iam_binding "owners" {
  role = "roles/owner"
  members = var.owners
}
resource google_project_iam_binding "editors" {
  role = "roles/editor"
  members = concat(var.editors, [var.appengine_deployer])
}
resource google_project_iam_binding "viewers" {
  role = "roles/viewer"
  members = var.viewers
}
