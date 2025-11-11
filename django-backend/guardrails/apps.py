from django.apps import AppConfig

class GuardrailsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'guardrails'
    verbose_name = "Guardrails for LLM-integrated apps"
