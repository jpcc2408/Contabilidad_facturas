# C:\Users\admin\facturacion\clientes\urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('lista/', views.cliente_lista, name='cliente_lista'),
    path('nuevo/', views.cliente_nuevo, name='cliente_nuevo'),
    path('<int:pk>/', views.cliente_detalle, name='cliente_detalle'),
    path('<int:pk>/editar-factura/', views.cliente_editar_factura, name='cliente_editar_factura'),
    path('facturas/pendientes/', views.facturas_pendientes, name='facturas_pendientes'),
    path('facturas/emitidas/', views.facturas_emitidas, name='facturas_emitidas'),
    path('facturas/pagadas/', views.facturas_pagadas, name='facturas_pagadas'),
    path('exportar/<str:formato>/', views.exportar_facturas, name='exportar_facturas'),
    path('<int:pk>/eliminar/', views.cliente_eliminar, name='cliente_eliminar'),
    path('<int:pk>/imprimir-factura/', views.imprimir_factura, name='imprimir_factura'),
    path('buscar-cliente/', views.buscar_cliente_por_nit, name='buscar_cliente_por_nit'),
]