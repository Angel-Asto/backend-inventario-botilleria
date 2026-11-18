from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Proveedor(models.Model):
    nombre = models.CharField(max_length=120)
    contacto = models.CharField(max_length=120)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'proveedores'

    def __str__(self):
        return self.nombre

