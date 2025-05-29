
from rest_framework import serializers
from decimal import Decimal
from .models import Organization, Payment


class PaymentWebhookSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    amount = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    payer_inn = serializers.CharField(
        min_length=10, 
        max_length=12,
        help_text="ИНН организации (10 или 12 цифр)"
    )
    document_number = serializers.CharField(max_length=255)
    document_date = serializers.DateTimeField()

    def validate_payer_inn(self, value):
        """Проверка валидности ИНН"""
        if not value.isdigit():
            raise serializers.ValidationError("ИНН должен содержать только цифры")
        if len(value) not in (10, 12):
            raise serializers.ValidationError("ИНН должен быть 10 или 12 символов")
        return value

    def validate_operation_id(self, value):
        """Проверка уникальности operation_id"""
        if Payment.objects.filter(operation_id=value).exists():
            raise serializers.ValidationError("Операция с таким ID уже существует")
        return value


class OrganizationBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['inn', 'balance']
        read_only_fields = ['inn', 'balance']


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['inn', 'balance']