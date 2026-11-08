from django.contrib import admin
from .models import UserProfile, UserOpinion, Contact

# Register your models here.


class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'county', 'is_read', 'created_at')
    list_filter = ('is_read', 'county', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Message Details', {
            'fields': ('subject', 'message')
        }),
        ('Categorization', {
            'fields': ('county', 'is_read')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'county', 'role', 'date_joined')
    list_filter = ('role', 'county', 'date_joined')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('date_joined', 'updated_at')
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone_number')
        }),
        ('Location & Role', {
            'fields': ('county', 'role')
        }),
        ('Additional Information', {
            'fields': ('bio', 'date_of_birth')
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class UserOpinionAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'opinion_type', 'county', 'status', 'created_at')
    list_filter = ('opinion_type', 'status', 'county', 'created_at', 'is_public')
    search_fields = ('user__username', 'subject', 'message', 'department')
    readonly_fields = ('created_at', 'updated_at', 'response_date')
    fieldsets = (
        ('Opinion Information', {
            'fields': ('user', 'opinion_type', 'subject', 'message')
        }),
        ('Categorization', {
            'fields': ('county', 'department', 'rating')
        }),
        ('Status & Visibility', {
            'fields': ('status', 'is_public')
        }),
        ('Admin Response', {
            'fields': ('admin_response', 'response_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        from django.utils import timezone
        if obj.admin_response and not obj.response_date:
            obj.response_date = timezone.now()
            obj.status = 'acknowledged'
        super().save_model(request, obj, form, change)

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserOpinion, UserOpinionAdmin)
admin.site.register(Contact, ContactAdmin)
