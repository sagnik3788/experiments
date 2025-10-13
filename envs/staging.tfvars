# staging.tfvars - environment values for staging

# Image that will be deployed by the webhook agent.
# The agent replaces this line with the new image reference.
image = "sagnik3788/promptsafely:13cfb884827dbb48e0b7f1a24511a44e6a08182a"
# Example additional vars
replica_count = 2
service_port = 8080
environment = "staging"
