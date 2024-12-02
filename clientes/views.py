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
import xlsxwriter

def es_admin(user):
    try:
        return user.rol == 'admin'
    except:
        return False

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
                
                # Obtener o crear usuario
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
                    cliente.base = cliente.total_factura / (1 + cliente.impuesto/100)
                    cliente.iva = cliente.total_factura - cliente.base
                
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
    cliente = get_object_or_404(Cliente, correlativo=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            cliente = form.save(commit=False)
            if cliente.total_factura and cliente.impuesto:
                cliente.base = cliente.total_factura / (1 + cliente.impuesto/100)
                cliente.iva = cliente.total_factura - cliente.base
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
    
    return HttpResponse('Formato no válido')