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
]