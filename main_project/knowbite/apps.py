from django.apps import AppConfig


class KnowbiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'knowbite'
    
    def ready(self):
        import knowbite.signals  # Connect the signals
