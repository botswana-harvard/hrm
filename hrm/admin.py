from django.contrib import admin

from .models import Employee, Hrm, VipMonthly, HrmMonthly


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_number', 'lastname', 'firstname', 'location', 'subunit')
    search_fields = ('employee_number', 'lastname', 'firstname')
    list_filter = ('location', 'subunit')


@admin.register(Hrm)
class HrmAdmin(admin.ModelAdmin):
    list_display = ('employee', 'hrm_balance', 'vip_balance',
                    'entitlements', 'pending_approval', 'scheduled',
                    'taken', 'available_balance')
    search_fields = ('employee__employee_number', 'employee__lastname',
                     'employee__firstname')
    list_filter = ('employee__location', 'employee__subunit')


@admin.register(HrmMonthly)
class HrmMonthlyAdmin(admin.ModelAdmin):
    list_display = ('employee', 'balance')
    list_filter = ('employee__location', 'employee__subunit')
    search_fields = ('employee__employee_number', 'employee__lastname',
                     'employee__firstname')


@admin.register(VipMonthly)
class VipMonthlyAdmin(admin.ModelAdmin):
    list_display = ('employee', 'balance')
    list_filter = ('employee__location', 'employee__subunit')
    search_fields = ('employee__employee_number', 'employee__lastname',
                     'employee__firstname')
