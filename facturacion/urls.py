# C:\Users\admin\facturacion\facturacion\urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
   path('admin/', admin.site.urls),
   path('', auth_views.LoginView.as_view(
       template_name='registration/login.html',
       redirect_authenticated_user=True,
       extra_context={'next': 'dashboard'}
   ), name='login'),
   path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
   path('clientes/', include('clientes.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)