from django.db import models
class users(models.Model):
    phone=models.IntegerField(unique=True)
    password=models.CharField(max_length=16)
class userinformation(models.Model):
    phone=models.IntegerField(unique=True)
    company=models.CharField(max_length=16)
    address=models.CharField(max_length=40)
    money=models.DecimalField(default=0,max_digits=12,decimal_places=2)
class watermark(models.Model):
    phone=models.IntegerField()
    upload_time=models.CharField(max_length=20)
    syspath=models.CharField(max_length=30,default="")
    filename=models.CharField(max_length=15,default="")
class cost(models.Model):
    phone = models.IntegerField()
    cost_time=models.CharField(max_length=40)
    cost_value=models.DecimalField(max_digits=12,decimal_places=2)
    cost_state=models.IntegerField()
# Create your models here.