variable "suffix" {
  description = "The pub/sub topic suffix"
  type        = string
  default     = "4242"
}

variable "project" {
  description = "The project to deploy the pub/sub topic to"
  type        = string
}
