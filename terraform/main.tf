resource "juju_application" "mysql_router" {
  model_uuid = var.model
  name       = var.app_name

  charm {
    name     = "mysql-router"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }

  config      = var.config
  constraints = var.constraints
  units       = var.units
}
