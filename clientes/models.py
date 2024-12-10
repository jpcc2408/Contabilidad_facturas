from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    ROLES = [
        ('admin', 'Administrador'),
        ('standard', 'Usuario Estándar'),
    ]
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='Los grupos a los que pertenece este usuario.',
        related_name='usuario_set'
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Permisos específicos para este usuario.',
        related_name='usuario_set'
    )
    
    rol = models.CharField(
        max_length=10, 
        choices=ROLES, 
        default='standard',
        verbose_name='Rol del usuario'
    )
    departamento = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name='Departamento'
    )
    telefono = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name='Teléfono'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Usuario activo'
    )

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        
    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"


class Cliente(models.Model):
    MONEDAS = [
        ('USD', 'Dólares'),
        ('EUR', 'Euros'), 
        ('GTQ', 'Quetzales'),
    ]
    
    TIPO_IMPUESTO = [
        ('AFECTO', 'Afecto'),
        ('EXENTO', 'Exento'),
    ]
    
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clientes_creados'
    )
    correlativo = models.AutoField(primary_key=True)
    razon_social = models.CharField(max_length=200)
    nit = models.CharField(max_length=20) 
    direccion = models.TextField()
    no_propuesta = models.CharField(max_length=50)
    codigo = models.CharField(max_length=50)
    concepto = models.TextField(blank=True)
    proyecto = models.CharField(max_length=100)
    socio = models.CharField(max_length=100)
    encargado = models.CharField(max_length=100)
    moneda = models.CharField(max_length=3, choices=MONEDAS)
    tipo_cambio = models.DecimalField(max_digits=10, decimal_places=2)
    impuesto = models.CharField(
        max_length=10,
        choices=TIPO_IMPUESTO,
        default='AFECTO',
        verbose_name='Tipo de Impuesto'
    )
    total_factura = models.DecimalField(max_digits=15, decimal_places=2)
    base = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_solicitud = models.DateField(null=True, blank=True, verbose_name='Fecha de Solicitud')  # Editable
    persona_recibe = models.CharField(max_length=100)
    correo_recibe = models.EmailField()
    correo_cliente = models.EmailField()
    solicitante = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_emision = models.DateField(null=True, blank=True)
    serie = models.CharField(max_length=10, null=True, blank=True)
    factura = models.CharField(max_length=20, null=True, blank=True)
    autorizacion = models.CharField(max_length=50, null=True, blank=True) 
    estado_factura = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    recibo_operado = models.CharField(max_length=50, null=True, blank=True)
    archivo_factura = models.FileField(
        upload_to='facturas/',
        null=True,
        blank=True,
        verbose_name='Archivo de Factura'
    )

    class Meta:
        indexes = [
            models.Index(fields=['correlativo']),
            models.Index(fields=['razon_social']),
        ]

    def __str__(self):
        return f"{self.correlativo} - {self.razon_social}"
