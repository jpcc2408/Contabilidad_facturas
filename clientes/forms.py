from datetime import datetime
from django import forms
from .models import Cliente

class ClienteForm(forms.ModelForm):    
  class Meta:
      model = Cliente
      fields = '__all__'
      exclude = ['correlativo', 'fecha_creacion', 'creado_por']
      widgets = {
          'tipo_impuesto': forms.Select(choices=[
              ('', 'Seleccione tipo de impuesto'),
              ('AFECTO', 'Afecto'),
              ('EXENTO', 'Exento')
          ]),
          'fecha_solicitud': forms.DateInput(
              attrs={
                  'type': 'date',
                  'readonly': True,
                  'value': datetime.now().strftime('%Y-%m-%d')
              }
          ),
          'fecha_emision': forms.DateInput(attrs={'type': 'date'}),
          'concepto': forms.Textarea(attrs={'rows': 3}),
          'direccion': forms.Textarea(attrs={'rows': 2}),
          'estado_factura': forms.Select(choices=[
              ('', 'Seleccione estado'),
              ('Pendiente', 'Pendiente'),
              ('Emitida', 'Emitida'),
              ('Pagada', 'Pagada')
          ]),
          'status': forms.Select(choices=[
              ('', 'Seleccione status'),
              ('Activo', 'Activo'),
              ('Inactivo', 'Inactivo')
          ])
      }
      
  def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      for field in self.fields:
          self.fields[field].widget.attrs.update({'class': 'form-control'})
      
      # Ocultar campos de factura en nuevo cliente
      if not kwargs.get('instance'):
          campos_factura = ['fecha_emision', 'serie', 'factura', 'autorizacion', 
                          'estado_factura', 'status', 'recibo_operado']
          for campo in campos_factura:
              if campo in self.fields:
                  self.fields[campo].widget = forms.HiddenInput()

  def clean(self):
      cleaned_data = super().clean()
      print("Datos limpiados:", cleaned_data)  # Debug
      return cleaned_data