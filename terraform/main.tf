resource "juju_application" "mysql_router" {
  name  = var.app_name
  model = var.model_name

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
