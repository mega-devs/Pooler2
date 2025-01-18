from django.db import models

class UFWRule(models.Model):
    DIRECTION_CHOICES = [
        ('in', 'Inbound'),
        ('out', 'Outbound'),
    ]
    PROTOCOL_CHOICES = [
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
        ('any', 'Any'),
    ]

    direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES, default='in')
    protocol = models.CharField(max_length=5, choices=PROTOCOL_CHOICES, default='tcp')
    port = models.IntegerField(blank=True, null=True)
    from_ip = models.CharField(max_length=35, blank=True, null=True)
    to_ip = models.CharField(max_length=35, blank=True, null=True)
    action = models.CharField(max_length=35, default='allow')
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.direction} {self.protocol} port {self.port} from {self.from_ip} to {self.to_ip} - {self.action}"