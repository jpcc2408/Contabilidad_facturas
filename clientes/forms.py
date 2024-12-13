from django import forms
from decimal import Decimal
from datetime import datetime
from .models import Cliente

class ClienteForm(forms.ModelForm):    
    class Meta:
        model = Cliente
        exclude = ['creado_por']
        
        widgets = {
            'fecha_solicitud': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control date-input',
                    'value': datetime.now().strftime('%Y-%m-%d'),
                    'data-bs-toggle': 'tooltip',
                    'title': 'Seleccione la fecha de solicitud'
                }
            ),
            'fecha_emision': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'concepto': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
            'direccion': forms.Textarea(
                attrs={'rows': 2, 'class': 'form-control'}
            ),
            'base': forms.NumberInput(
                attrs={'readonly': 'readonly', 'class': 'form-control'}
            ),
            'iva': forms.NumberInput(
                attrs={'readonly': 'readonly', 'class': 'form-control'}
            ),
            'estado_factura': forms.HiddenInput(),
            'status': forms.HiddenInput(),
            'cliente': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'archivo_factura': forms.FileInput(
                attrs={'class': 'form-control'}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar fecha
        self.fields['fecha_solicitud'].label = 'Fecha de Solicitud 📅'
        self.fields['fecha_solicitud'].help_text = 'Fecha en que se realiza la solicitud'
        self.fields['fecha_solicitud'].initial = datetime.now().date()
        
        # Valores iniciales
        if not self.instance.pk:  # Solo para nuevos registros
            self.fields['tipo_cambio'].initial = 1.00
            self.fields['moneda'].initial = 'GTQ'
            self.fields['impuesto'].initial = 'AFECTO'
            self.fields['estado_factura'].initial = 'PENDIENTE'
            self.fields['status'].initial = 'ACTIVO'

        # Campos no requeridos
        optional_fields = [
            'cliente', 'persona_recibe', 'concepto', 
            'fecha_emision', 'serie', 'factura', 
            'autorizacion', 'recibo_operado', 'archivo_factura'
        ]
        for field in optional_fields:
            self.fields[field].required = False

        # Mensajes de ayuda
        self.fields['total_factura'].help_text = 'Ingrese el monto total incluyendo IVA'
        self.fields['tipo_cambio'].help_text = 'Tasa de cambio respecto al Quetzal'
        self.fields['nit'].help_text = 'Ingrese el NIT sin guiones ni espacios'

    def clean(self):
        cleaned_data = super().clean()
        
        if not cleaned_data.get('cliente'):
            cleaned_data['cliente'] = cleaned_data.get('razon_social')

        total_factura = cleaned_data.get('total_factura')
        impuesto = cleaned_data.get('impuesto')

        if total_factura and impuesto:
            if impuesto == 'AFECTO':
                base = total_factura / Decimal('1.12')
                iva = total_factura - base
            else:
                base = total_factura
                iva = Decimal('0')

            cleaned_data['base'] = round(base, 2)
            cleaned_data['iva'] = round(iva, 2)

        return cleaned_data

    def clean_nit(self):
        nit = self.cleaned_data.get('nit')
        if nit:
            nit = nit.replace(' ', '').replace('-', '')
        return nit