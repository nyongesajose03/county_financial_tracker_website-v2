from django.urls import path
from webapp import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('project-tracker/', views.project_tracker, name='project_tracker'),
    path('qrcode/', views.qrcode_page, name='qrcode'),
    path('budget/', views.budget_page, name='budget'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('finance/', views.finance, name='finance'),
    path('expenditure/', views.expenditure_page, name='expenditure'),
    path('revenue/', views.revenue_page, name='revenue'),
    path('finance/data/', views.finance_data, name='finance_data'),
    path(
        'finance/annual-allocation-data/',
        views.annual_allocation_data,
        name='annual_allocation_data',
    ),
    path(
        'finance/monthly-allocation-data/',
        views.monthly_allocation_data,
        name='monthly_allocation_data',
    ),
    path(
        'finance/report-data/',
        views.financial_report_data,
        name='financial_report_data',
    ),
    path('settings/', views.settings_page, name='settings'),
    path('about/', views.about_feedback, name='about_feedback'),
    path('opinion/submit/', views.submit_opinion, name='submit_opinion'),
    path('opinion/my-opinions/', views.view_opinions, name='view_opinions'),
    path('opinion/public/', views.public_opinions, name='public_opinions'),
    path('contact/', views.contact, name='contact')
]
