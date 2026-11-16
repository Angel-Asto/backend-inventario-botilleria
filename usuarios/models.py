from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        TRABAJADOR = 'trabajador', 'Trabajador'

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.TRABAJADOR)

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN or self.is_superuser

    def __str__(self):
        return self.get_full_name() or self.username