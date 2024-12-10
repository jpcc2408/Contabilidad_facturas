from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.http import HttpResponse
from django.core.paginator import Paginator
from datetime import datetime
from decimal import Decimal
from .models import Cliente, Usuario
from .forms import ClienteForm
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from reportlab.lib import colors
import xlsxwriter


def es_admin(user):
    if not user or not user.is_authenticated:
        return False
    
    if not hasattr(user, 'rol'):
        print(f"Error: El usuario {user.username} no tiene atributo 'rol'")
        return False
        
    return user.rol == 'admin'







@login_required
def dashboard(request):
    total_clientes = Cliente.objects.count()
    facturas_pendientes = Cliente.objects.filter(estado_factura='Pendiente').count()
    facturas_emitidas = Cliente.objects.filter(estado_factura='Emitida').count()
    facturas_pagadas = Cliente.objects.filter(estado_factura='Pagada').count()
    
    total_quetzales = Cliente.objects.filter(
        moneda='GTQ',
        estado_factura__in=['Emitida', 'Pagada']
    ).aggregate(total=Sum('total_factura'))['total'] or 0
    
    total_dolares = Cliente.objects.filter(
        moneda='USD',
        estado_factura__in=['Emitida', 'Pagada']
    ).aggregate(total=Sum('total_factura'))['total'] or 0
    
    clientes_recientes = Cliente.objects.all().order_by('-fecha_creacion')[:5]
    
    facturas_por_mes = Cliente.objects.filter(
        fecha_solicitud__year=datetime.now().year
    ).values('fecha_solicitud__month').annotate(
        total=Sum('total_factura')
    ).order_by('fecha_solicitud__month')
    
    context = {
        'total_clientes': total_clientes,
        'facturas_pendientes': facturas_pendientes,
        'facturas_emitidas': facturas_emitidas,
        'facturas_pagadas': facturas_pagadas,
        'total_quetzales': total_quetzales,
        'total_dolares': total_dolares,
        'clientes_recientes': clientes_recientes,
        'facturas_por_mes': facturas_por_mes,
        'now': datetime.now(),
    }
    return render(request, 'clientes/dashboard.html', context)

@login_required
def cliente_lista(request):
    # Filtrar por usuario según rol
    try:
        if es_admin(request.user):
            queryset = Cliente.objects.all()
        else:
            queryset = Cliente.objects.filter(creado_por=request.user)
    except:
        queryset = Cliente.objects.all()

    # Búsqueda general
    busqueda = request.GET.get('q')
    if busqueda:
        queryset = queryset.filter(
            Q(razon_social__icontains=busqueda) |
            Q(nit__icontains=busqueda) |
            Q(proyecto__icontains=busqueda)
        )

    # Filtros específicos
    estado = request.GET.get('estado')
    if estado:
        queryset = queryset.filter(estado_factura=estado)

    moneda = request.GET.get('moneda')
    if moneda:
        queryset = queryset.filter(moneda=moneda)

    # Ordenamiento
    orden = request.GET.get('orden', '-correlativo')
    queryset = queryset.order_by(orden)

    # Estadísticas
    total_registros = queryset.count()
    total_pendientes = queryset.filter(estado_factura='Pendiente').count()
    total_emitidas = queryset.filter(estado_factura='Emitida').count()
    total_pagadas = queryset.filter(estado_factura='Pagada').count()

    # Totales por moneda
    totales_por_moneda = queryset.values('moneda').annotate(
        total=Sum('total_factura')
    )

    # Paginación
    paginator = Paginator(queryset, 10)
    pagina = request.GET.get('page', 1)
    try:
        clientes = paginator.page(pagina)
    except:
        clientes = paginator.page(1)

    context = {
        'clientes': clientes,
        'total_registros': total_registros,
        'total_pendientes': total_pendientes,
        'total_emitidas': total_emitidas,
        'total_pagadas': total_pagadas,
        'totales_por_moneda': totales_por_moneda,
        'parametros': request.GET.urlencode(),
    }
    
    return render(request, 'clientes/cliente_lista.html', context)

@login_required
def cliente_nuevo(request):
   if request.method == "POST":
       form = ClienteForm(request.POST)
       print("Datos del POST:", request.POST)
       if form.is_valid():
           print("Formulario válido")
           try:
               cliente = form.save(commit=False)
               
               try:
                   usuario = Usuario.objects.get(username=request.user.username)
               except Usuario.DoesNotExist:
                   usuario = Usuario.objects.create(
                       username=request.user.username,
                       email=request.user.email,
                       first_name=request.user.first_name,
                       last_name=request.user.last_name,
                       rol='standard'
                   )
               
               cliente.creado_por = usuario
               cliente.estado_factura = 'Pendiente'
               
               if cliente.total_factura and cliente.impuesto:
                   if cliente.impuesto == 'EXENTO':
                       cliente.base = cliente.total_factura
                       cliente.iva = 0
                   elif cliente.impuesto == 'AFECTO':
                       cliente.base = cliente.total_factura / Decimal('1.12')
                       cliente.iva = cliente.base * Decimal('0.12')
               
               cliente.save()
               print("Cliente guardado exitosamente")
               messages.success(request, f'Cliente {cliente.razon_social} creado exitosamente!')
               return redirect('cliente_lista')
           except Exception as e:
               print("Error al guardar:", str(e))
               messages.error(request, f'Error al guardar: {str(e)}')
       else:
           print("Errores del formulario:", form.errors)
           messages.error(request, 'Por favor corrija los errores en el formulario.')
   else:
       form = ClienteForm()
   
   return render(request, 'clientes/cliente_form.html', {'form': form})

@login_required
def cliente_detalle(request, pk):
   try:
       if es_admin(request.user):
           cliente = get_object_or_404(Cliente, correlativo=pk)
       else:
           try:
               cliente = Cliente.objects.get(correlativo=pk, creado_por=request.user)
           except Cliente.DoesNotExist:
               messages.warning(request, f'⚠️ ACCESO DENEGADO: No tienes autorización para ver esta factura. Solo puedes ver las facturas creadas por ti.')
               return redirect('cliente_lista')
       
       if request.method == "POST":
           form = ClienteForm(request.POST, instance=cliente)
           if form.is_valid():
               cliente = form.save(commit=False)
               if cliente.total_factura and cliente.impuesto:
                   if cliente.impuesto == 'EXENTO':
                       cliente.base = cliente.total_factura
                       cliente.iva = 0
                   elif cliente.impuesto == 'AFECTO':
                       cliente.base = cliente.total_factura / Decimal('1.12')
                       cliente.iva = cliente.base * Decimal('0.12')
               cliente.save()
               messages.success(request, 'Datos actualizados exitosamente!')
               return redirect('cliente_lista')
           else:
               messages.error(request, 'Por favor corrija los errores en el formulario.')
       else:
           form = ClienteForm(instance=cliente)

       return render(request, 'clientes/cliente_detalle.html', {
           'cliente': cliente,
           'form': form,
           'is_update': True
       })
   except Exception as e:
       messages.error(request, 'Ha ocurrido un error al acceder a la factura.')
       return redirect('cliente_lista')



@login_required
def cliente_editar_factura(request, pk):
    cliente = get_object_or_404(Cliente, correlativo=pk)
    
    if request.method == "POST":
        try:
            fecha_str = request.POST.get('fecha_emision')
            fecha_emision = None
            if fecha_str:
                fecha_emision = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                
            cliente.fecha_emision = fecha_emision
            cliente.serie = request.POST.get('serie')
            cliente.factura = request.POST.get('factura')
            cliente.autorizacion = request.POST.get('autorizacion')
            cliente.estado_factura = request.POST.get('estado_factura')
            cliente.status = request.POST.get('status')
            cliente.recibo_operado = request.POST.get('recibo_operado')
            
            # Manejo del archivo
            archivo = request.FILES.get('archivo_factura')
            if archivo:
                cliente.archivo_factura = archivo
            
            cliente.save()
            messages.success(request, 'Datos de facturación actualizados exitosamente!')
        except Exception as e:
            messages.error(request, f'Error al actualizar los datos: {str(e)}')
            
        return redirect('cliente_detalle', pk=pk)
    
    return render(request, 'clientes/cliente_editar_factura.html', {
        'cliente': cliente,
        'estados_factura': [
            ('Pendiente', 'Pendiente'),
            ('Emitida', 'Emitida'),
            ('Pagada', 'Pagada')
        ],
        'estados_status': [
            ('Activo', 'Activo'),
            ('Inactivo', 'Inactivo')
        ]
    })

@login_required
def facturas_pendientes(request):
    if es_admin(request.user):
        queryset = Cliente.objects.filter(estado_factura='Pendiente')
    else:
        queryset = Cliente.objects.filter(
            estado_factura='Pendiente',
            creado_por=request.user
        )
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(fecha_solicitud__range=[fecha_inicio, fecha_fin])
        except ValueError:
            messages.error(request, 'Formato de fecha inválido')

    orden = request.GET.get('orden', '-fecha_solicitud')
    queryset = queryset.order_by(orden)

    totales = queryset.values('moneda').annotate(
        total=Sum('total_factura'),
        cantidad=Count('correlativo')
    )

    paginator = Paginator(queryset, 10)
    pagina = request.GET.get('page', 1)
    try:
        facturas = paginator.page(pagina)
    except:
        facturas = paginator.page(1)

    context = {
        'facturas': facturas,
        'totales': totales,
        'titulo': 'Facturas Pendientes',
        'parametros': request.GET.urlencode()
    }
    
    return render(request, 'clientes/facturas_pendientes.html', context)

@login_required
def facturas_emitidas(request):
    if es_admin(request.user):
        queryset = Cliente.objects.filter(estado_factura='Emitida')
    else:
        queryset = Cliente.objects.filter(
            estado_factura='Emitida',
            creado_por=request.user
        )
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(fecha_emision__range=[fecha_inicio, fecha_fin])
        except ValueError:
            messages.error(request, 'Formato de fecha inválido')

    orden = request.GET.get('orden', '-fecha_emision')
    queryset = queryset.order_by(orden)

    totales = queryset.values('moneda').annotate(
        total=Sum('total_factura'),
        cantidad=Count('correlativo')
    )

    paginator = Paginator(queryset, 10)
    pagina = request.GET.get('page', 1)
    try:
        facturas = paginator.page(pagina)
    except:
        facturas = paginator.page(1)

    context = {
        'facturas': facturas,
        'totales': totales,
        'titulo': 'Facturas Emitidas',
        'parametros': request.GET.urlencode()
    }
    
    return render(request, 'clientes/facturas_emitidas.html', context)

@login_required
def facturas_pagadas(request):
    if es_admin(request.user):
        queryset = Cliente.objects.filter(estado_factura='Pagada')
    else:
        queryset = Cliente.objects.filter(
            estado_factura='Pagada',
            creado_por=request.user
        )
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(fecha_emision__range=[fecha_inicio, fecha_fin])
        except ValueError:
            messages.error(request, 'Formato de fecha inválido')

    orden = request.GET.get('orden', '-fecha_emision')
    queryset = queryset.order_by(orden)

    totales = queryset.values('moneda').annotate(
        total=Sum('total_factura'),
        cantidad=Count('correlativo')
    )

    paginator = Paginator(queryset, 10)
    pagina = request.GET.get('page', 1)
    try:
        facturas = paginator.page(pagina)
    except:
        facturas = paginator.page(1)

    context = {
        'facturas': facturas,
        'totales': totales,
        'titulo': 'Facturas Pagadas',
        'parametros': request.GET.urlencode()
    }
    
    return render(request, 'clientes/facturas_pagadas.html', context)

@login_required
def exportar_facturas(request, formato):
    if es_admin(request.user):
        queryset = Cliente.objects.all()
    else:
        queryset = Cliente.objects.filter(creado_por=request.user)
    
    busqueda = request.GET.get('q')
    if busqueda:
        queryset = queryset.filter(
            Q(razon_social__icontains=busqueda) |
            Q(nit__icontains=busqueda) |
            Q(proyecto__icontains=busqueda)
        )

    estado = request.GET.get('estado')
    if estado:
        queryset = queryset.filter(estado_factura=estado)

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            queryset = queryset.filter(fecha_solicitud__range=[fecha_inicio, fecha_fin])
        except ValueError:
            messages.error(request, 'Formato de fecha inválido')

    orden = request.GET.get('orden', '-correlativo')
    queryset = queryset.order_by(orden)

    if formato == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="facturas.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Correlativo', 'Razón Social', 'NIT', 'Proyecto', 'Fecha Solicitud', 
                        'Moneda', 'Total', 'Estado', 'Serie', 'Factura', 'Fecha Emisión'])
        
        for factura in queryset:
            writer.writerow([
                factura.correlativo,
                factura.razon_social,
                factura.nit,
                factura.proyecto,
                factura.fecha_solicitud,
                factura.moneda,
                factura.total_factura,
                factura.estado_factura,
                factura.serie or '',
                factura.factura or '',
                factura.fecha_emision or ''
            ])
        
        return response
        
    elif formato == 'pdf':
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="facturas.pdf"'
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Título
        p.setFont("Helvetica-Bold", 14)
        p.drawString(250, 750, "Listado de Facturas")
        
        # Fecha de generación
        p.setFont("Helvetica", 10)
        p.drawString(50, 730, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        # Encabezados
        y = 700
        p.setFont("Helvetica-Bold", 10)
        headers = ['Correlativo', 'Razón Social', 'NIT', 'Total', 'Estado']
        x_positions = [50, 120, 300, 380, 450]
        
        for header, x in zip(headers, x_positions):
            p.drawString(x, y, header)
        
        # Datos
        y -= 20
        p.setFont("Helvetica", 10)
        for factura in queryset:
            if y <= 50:  # Nueva página si no hay espacio
                p.showPage()
                p.setFont("Helvetica", 10)
                y = 750
            
            datos = [
                str(factura.correlativo),
                factura.razon_social[:30],
                factura.nit,
                f"{factura.moneda} {factura.total_factura:,.2f}",
                factura.estado_factura or 'Pendiente'
            ]
            
            for dato, x in zip(datos, x_positions):
                p.drawString(x, y, str(dato))
            
            y -= 20
        
        p.showPage()
        p.save()
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response

    elif formato == 'excel':
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="facturas.xlsx"'
        
        workbook = xlsxwriter.Workbook(response)
        worksheet = workbook.add_worksheet()
        
        # Estilos
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#F7F7F7',
            'border': 1
        })
        
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        
        # Encabezados
        headers = ['Correlativo', 'Razón Social', 'NIT', 'Proyecto', 'Fecha Solicitud',
                  'Moneda', 'Total', 'Estado', 'Serie', 'Factura', 'Fecha Emisión']
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 15)
        
        for row, factura in enumerate(queryset, start=1):
            worksheet.write(row, 0, factura.correlativo)
            worksheet.write(row, 1, factura.razon_social)
            worksheet.write(row, 2, factura.nit)
            worksheet.write(row, 3, factura.proyecto)
            worksheet.write(row, 4, factura.fecha_solicitud, date_format)
            worksheet.write(row, 5, factura.moneda)
            worksheet.write(row, 6, float(factura.total_factura), number_format)
            worksheet.write(row, 7, factura.estado_factura or 'Pendiente')
            worksheet.write(row, 8, factura.serie or '')
            worksheet.write(row, 9, factura.factura or '')
            worksheet.write(row, 10, factura.fecha_emision, date_format if factura.fecha_emision else None)
        
        workbook.close()
        return response

@login_required
def cliente_eliminar(request, pk):
    try:
        if not es_admin(request.user):
            messages.warning(request, '⚠️ ACCESO DENEGADO: Solo los administradores pueden eliminar facturas.')
            return redirect('cliente_lista')
        
        cliente = get_object_or_404(Cliente, correlativo=pk)
        
        if request.method == "POST":
            razon_social = cliente.razon_social  # Guardamos el nombre para el mensaje
            cliente.delete()
            messages.success(request, f'✅ La factura del cliente "{razon_social}" ha sido eliminada exitosamente.')
            return redirect('cliente_lista')
            
        return render(request, 'clientes/cliente_eliminar.html', {
            'cliente': cliente
        })
        
    except Exception as e:
        messages.error(request, '❌ Ha ocurrido un error al intentar eliminar la factura.')
        return redirect('cliente_lista')

@login_required
def imprimir_factura(request, pk):
    try:
        cliente = get_object_or_404(Cliente, correlativo=pk)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="factura_{cliente.correlativo}.pdf"'
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Colores
        azul_header = colors.HexColor('#1a56db')      # Azul más corporativo
        gris_texto = colors.HexColor('#374151')       # Gris oscuro para texto
        verde_badge = colors.HexColor('#059669')      # Verde para estados

        # Header
        p.setFillColor(azul_header)
        p.rect(0, height - 80, width, 80, fill=True)
        
        # Contenido del header
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 22)
        p.drawString(50, height - 35, "GRUPO CFE")
        p.setFont("Helvetica", 11)
        p.drawString(50, height - 55, f"Factura #{cliente.correlativo}")
        p.drawString(50, height - 70, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")

        # Total en header
        p.setFont("Helvetica-Bold", 12)
        p.drawString(400, height - 35, "TOTAL")
        p.setFont("Helvetica-Bold", 18)
        p.drawString(400, height - 60, f"{cliente.moneda} {cliente.total_factura:,.2f}")

        # Sección Facturar A
        y = height - 120
        p.setFillColor(gris_texto)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "FACTURAR A")
        
        p.setFont("Helvetica", 10)
        y -= 20
        p.drawString(50, y, cliente.razon_social)
        y -= 15
        p.drawString(50, y, f"NIT: {cliente.nit}")
        y -= 15
        p.drawString(50, y, cliente.direccion)

        # Detalles del Proyecto
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "DETALLES DEL PROYECTO")
        y -= 20

        # Crear cajas para detalles del proyecto
        detalles_proyecto = [
            ("Proyecto", cliente.proyecto),
            ("Socio", cliente.socio),
            ("Encargado", cliente.encargado),
            ("No. Propuesta", cliente.no_propuesta),
            ("Código", cliente.codigo)
        ]

        for label, value in detalles_proyecto:
            p.rect(50, y-15, width-100, 25)  # Caja
            p.setFont("Helvetica", 10)
            p.drawString(60, y, f"{label}: {value}")
            y -= 25

        # Detalle Financiero
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "DETALLE FINANCIERO")
        y -= 25

        detalles_financieros = [
            ("Base", cliente.base),
            ("IVA", cliente.iva),
            ("Impuesto", cliente.impuesto),
            ("Total", cliente.total_factura)
        ]

        for label, value in detalles_financieros:
            p.setFont("Helvetica", 10)
            p.drawString(50, y, label)
            p.drawString(400, y, f"{cliente.moneda} {value:,.2f}")
            y -= 20

        # Estado
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "ESTADO")
        y -= 25

        # Badge de estado
        estado = cliente.estado_factura or "Pendiente"
        p.setFillColor(verde_badge)
        p.roundRect(50, y-15, 70, 20, 6, fill=True)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(55, y-10, estado)

        # Contacto
        y -= 50
        p.setFillColor(gris_texto)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "CONTACTO")
        p.setFont("Helvetica", 10)
        y -= 20
        p.drawString(50, y, f"Email: {cliente.correo_cliente}")
        y -= 15
        p.drawString(50, y, f"Persona que recibe: {cliente.persona_recibe}")

        # Firmas
        y = 50
        p.line(50, y, 200, y)
        p.line(350, y, 500, y)
        p.setFont("Helvetica", 9)
        p.drawString(110, y-20, "Cliente")
        p.drawString(410, y-20, "Autorizado")

        p.showPage()
        p.save()
        
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
        
    except Exception as e:
        print(f"Error al generar factura: {str(e)}")
        messages.error(request, 'Ha ocurrido un error al generar la factura.')
        return redirect('cliente_lista')
    
    return HttpResponse('Formato no válido')