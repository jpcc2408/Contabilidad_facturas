from django.db import models
from django.contrib.auth.models import AbstractUser
from decimal import Decimal

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

class ClienteBase(models.Model):
    nit = models.CharField(
        max_length=20,
        verbose_name='NIT'
    )
    cliente = models.CharField(
        max_length=200,
        verbose_name='Cliente',
        null=True,
        blank=True
    )
    razon_social = models.CharField(
        max_length=200,
        verbose_name='Razón Social'
    )
    direccion = models.TextField(
        verbose_name='Dirección'
    )
    correo_cliente = models.EmailField(
        verbose_name='Correo del Cliente'
    )
    correo_recibe = models.EmailField(
        verbose_name='Correo de Recepción'
    )
    persona_recibe = models.CharField(
        max_length=100,
        verbose_name='Persona que Recibe'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )

    class Meta:
        db_table = 'clientes_base'  # Esto fuerza el nombre de la tabla
        verbose_name = 'Cliente Base'
        verbose_name_plural = 'Clientes Base'
        ordering = ['razon_social']
        indexes = [
            models.Index(fields=['nit']),
            models.Index(fields=['razon_social']),
        ]
    def __str__(self):
        return f"{self.razon_social} ({self.nit})"

class Cliente(models.Model):
    MONEDAS = [
        ('USD', 'Dólares'),
        ('EUR', 'Euros'), 
        ('GTQ', 'Quetzales'),
    ]
    
    TIPO_IMPUESTO = [
        ('AFECTO', 'Afecto (12%)'),
        ('EXENTO', 'No Afecto (0%)'),
    ]

    ESTADOS_FACTURA = [
        ('PENDIENTE', 'Pendiente'),
        ('EMITIDA', 'Emitida'),
        ('PAGADA', 'Pagada'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]
    
    # Campos de seguimiento
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clientes_creados'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Creación'
    )
    
    # Campos de identificación
    correlativo = models.AutoField(primary_key=True)
    cliente = models.CharField(
        max_length=200,
        verbose_name='Cliente',
        help_text='Nombre del cliente o empresa',
        null=True,
        blank=True
    )
    razon_social = models.CharField(
        max_length=200,
        verbose_name='Razón Social'
    )
    nit = models.CharField(
        max_length=20,
        verbose_name='NIT'
    )
    direccion = models.TextField(
        verbose_name='Dirección'
    )
    correo_cliente = models.EmailField(
        verbose_name='Correo del Cliente'
    )
    correo_recibe = models.EmailField(
        verbose_name='Correo de Recepción'
    )
    persona_recibe = models.CharField(
        max_length=100,
        verbose_name='Persona que Recibe',
        null=True,
        blank=True
    )
    
    # Información del proyecto
    no_propuesta = models.CharField(
        max_length=50,
        verbose_name='No. de Propuesta'
    )
    codigo = models.CharField(
        max_length=50,
        verbose_name='Código'
    )
    concepto = models.TextField(
        blank=True,
        verbose_name='Concepto'
    )
    proyecto = models.CharField(
        max_length=100,
        verbose_name='Proyecto'
    )
    socio = models.CharField(
        max_length=100,
        verbose_name='Socio'
    )
    encargado = models.CharField(
        max_length=100,
        verbose_name='Encargado'
    )
    solicitante = models.CharField(
        max_length=100,
        verbose_name='Solicitante'
    )
    
    # Información financiera
    moneda = models.CharField(
        max_length=3,
        choices=MONEDAS,
        verbose_name='Moneda'
    )
    tipo_cambio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Tipo de Cambio'
    )
    impuesto = models.CharField(
        max_length=10,
        choices=TIPO_IMPUESTO,
        default='AFECTO',
        verbose_name='Tipo de Impuesto'
    )
    total_factura = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Total Factura'
    )
    base = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Base Imponible'
    )
    iva = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='IVA'
    )
    
    # Fechas
    fecha_solicitud = models.DateField(
        verbose_name='Fecha de Solicitud',
        default=models.functions.Now
    )
    fecha_emision = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Emisión'
    )
    
    # Información de facturación
    serie = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Serie'
    )
    factura = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='No. de Factura'
    )
    autorizacion = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='No. de Autorización'
    )
    estado_factura = models.CharField(
        max_length=20,
        choices=ESTADOS_FACTURA,
        default='PENDIENTE',
        verbose_name='Estado de Factura'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVO',
        verbose_name='Status'
    )
    recibo_operado = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Recibo Operado'
    )
    archivo_factura = models.FileField(
        upload_to='facturas/',
        null=True,
        blank=True,
        verbose_name='Archivo de Factura'
    )

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        indexes = [
            models.Index(fields=['correlativo']),
            models.Index(fields=['razon_social']),
            models.Index(fields=['nit']),
        ]

    def __str__(self):
        return f"{self.correlativo} - {self.razon_social}"

    def calcular_iva(self):
        """Calcula el IVA basado en el tipo de impuesto"""
        if self.impuesto == 'AFECTO':
            return self.total_factura * Decimal('0.12')
        return Decimal('0')

    def calcular_base(self):
        """Calcula la base imponible"""
        if self.impuesto == 'AFECTO':
            return self.total_factura / Decimal('1.12')
        return self.total_factura