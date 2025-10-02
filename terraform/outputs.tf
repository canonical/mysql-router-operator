output "app_name" {
  description = "Name of the MySQL Router VM application"
  value       = juju_application.mysql_router.name
}

output "provides" {
  description = "Map of all the provided endpoints"
  value = {
    database  = "database"
    cos_agent = "cos-agent"
  }
}

output "requires" {
  description = "Map of all the required endpoints"
  value = {
    backend_database = "backend-database"
    certificates     = "certificates"
    tracing          = "tracing"
  }
}
