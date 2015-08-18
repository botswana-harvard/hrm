from django.db import models


class Employee(models.Model):

    employee_number = models.CharField(
        max_length=10,
        unique=True,
    )

    firstname = models.CharField(
        max_length=100
    )

    lastname = models.CharField(
        max_length=100
    )

    middlename = models.CharField(
        max_length=100,
        null=True
    )

    subunit = models.CharField(
        max_length=100,
        null=True
    )

    location = models.CharField(
        max_length=100,
        null=True
    )

    job_title = models.CharField(
        max_length=100,
        null=True
    )

    employment_status = models.CharField(
        max_length=100,
        null=True
    )

    joined = models.DateField()

    strippedname = models.CharField(
        max_length=100,
        null=True
    )

    def __str__(self):
        return '{}, {} ({}) '.format(self.lastname, self.firstname, self.employee_number)

    def fullname(self):
        return '{} {} {}'.format(self.firstname, self.middlename, self.lastname)

    class Meta:
        app_label = 'hrm'
        unique_together = (('firstname', 'lastname'), )
        ordering = ('lastname', )


class Hrm(models.Model):

    employee = models.ForeignKey(Employee)

    fullname = models.CharField(
        max_length=100
    )

    leave_period_start = models.DateField()

    leave_period_end = models.DateField()

    entitlements = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    pending_approval = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    scheduled = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    taken = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    available_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    total_overdrawn = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    hrm_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    vip_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True
    )

    class Meta:
        app_label = 'hrm'
        ordering = ('employee__lastname', )


class Vip(models.Model):

    employee = models.ForeignKey(Employee)

    employee_number = models.CharField(
        max_length=100,
    )

    fullname = models.CharField(
        max_length=100
    )

    leave_period_start = models.DateField(null=True)

    leave_period_end = models.DateField(null=True)

    entitlements = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
    )

    pending_approval = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
    )

    scheduled = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
    )

    taken = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
    )

    available_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
    )

    total_overdrawn = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
    )

    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        app_label = 'hrm'
        ordering = ('employee__lastname', )
