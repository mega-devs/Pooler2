from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="email")
    phone = models.CharField(max_length=100, verbose_name="phone", null=True, blank=True)
    avatar = models.ImageField(upload_to="users/", verbose_name="avatar", null=True, blank=True)
    country = models.CharField(max_length=150, verbose_name="country", null=True, blank=True)
    token = models.CharField(max_length=100, verbose_name="token", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="is_active")
    is_staff = models.BooleanField(default=False, verbose_name="is_staff")


    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions_set',
        blank=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"