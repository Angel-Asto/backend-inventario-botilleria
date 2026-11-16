from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Rol en el sistema', {'fields': ('rol',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Rol en el sistema', {'fields': ('rol',)}),)
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_active')