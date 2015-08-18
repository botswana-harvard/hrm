from django.test.testcases import TestCase

from django.core.exceptions import MultipleObjectsReturned

from .models import Hrm, Vip, Employee
from .readers import HrmReader, VipReader, EmployeeReader


class TestHrm(TestCase):

    def setUp(self):
        csvfile = '~/source/hrm/hrm/data/employee.csv'
        reader = EmployeeReader(csvfile)
        reader.load()
        self.assertEqual(Employee.objects.all().count(), 300)

    def test_import_hrm(self):
        csvfile = '~/source/hrm/hrm/data/hrm.csv'
        hrm_reader = HrmReader(csvfile)
        hrm_reader.load()
        self.assertEqual(Hrm.objects.all().count(), 300)

    def test_import_vip(self):
        csvfile = '~/source/hrm/hrm/data/vip.csv'
        reader = VipReader(csvfile, 8, 2015)
        reader.load()
        self.assertEqual(Vip.objects.all().count(), 297)

    def test_match_employee(self):
        csvfile = '~/source/hrm/hrm/data/hrm.csv'
        hrm_reader = HrmReader(csvfile)
        hrm_reader.load()
        csvfile = '~/source/hrm/hrm/data/vip.csv'
        reader = VipReader(csvfile, 8, 2015)
        reader.load()
        for hrm in Hrm.objects.all():
            try:
                Vip.objects.get(employee=hrm.employee)
            except Vip.DoesNotExist:
                print(hrm.employee)
