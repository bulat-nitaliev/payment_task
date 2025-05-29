
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import F
from .models import Payment, Organization, BalanceLog
from .serializers import PaymentWebhookSerializer, OrganizationBalanceSerializer
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse

logger = logging.getLogger(__name__)

class PaymentWebhookAPIView(APIView):
    """APIView для обработки входящих платежных вебхуков"""
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        request=PaymentWebhookSerializer,
        examples=[
            OpenApiExample(
                'Example payload',
                value={
                    "operation_id": "ccf0a86d-041b-4991-bcf7-e2352f7b8a4a",
                    "amount": 145000,
                    "payer_inn": "1234567890",
                    "document_number": "PAY-328",
                    "document_date": "2024-04-27T21:00:00Z"
                },
                request_only=True
            )
        ],
        responses={
            200: OpenApiResponse(description='OK - Webhook processed or duplicate'),
            400: OpenApiResponse(description='Bad Request - Invalid input data'),
            500: OpenApiResponse(description='Internal Server Error')
        },
        description='Endpoint для обработки входящих платежных вебхуков от банка'
    )
    def post(self, request, *args, **kwargs):
        serializer = PaymentWebhookSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.warning(f"Invalid webhook data: {serializer.errors}")
            return Response(
                {"error": "Invalid data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            return self.process_valid_payment(serializer.validated_data)
        except Exception as e:
            logger.exception("Unexpected error in payment processing")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def process_valid_payment(self, data):
        """Обработка валидного платежа в транзакции"""
        with transaction.atomic():
            # Проверка дубля операции (дополнительная защита)
            if Payment.objects.filter(operation_id=data['operation_id']).exists():
                return Response(status=status.HTTP_200_OK)
            
            # Получаем или создаем организацию
            organization, created = Organization.objects.get_or_create(
                inn=data['payer_inn'],
                defaults={'balance': 0}
            )
            
            # Создаем платеж
            payment = Payment.objects.create(
                operation_id=data['operation_id'],
                amount=data['amount'],
                payer_inn=data['payer_inn'],
                document_number=data['document_number'],
                document_date=data['document_date']
            )
            
            # Атомарное обновление баланса
            Organization.objects.filter(id=organization.id).update(
                balance=F('balance') + payment.amount
            )
            
            # Обновляем объект организации
            organization.refresh_from_db()
            
            # Логируем изменение баланса
            BalanceLog.objects.create(
                organization=organization,
                payment=payment,
                amount=payment.amount,
                balance_after=organization.balance
            )
            
            logger.info(
                f"Payment processed: {payment.operation_id}, "
                f"Amount: {payment.amount}, "
                f"INN: {organization.inn}, "
                f"New balance: {organization.balance}"
            )
            
            return Response(status=status.HTTP_200_OK)


class OrganizationBalanceAPIView(APIView):
    """APIView для получения баланса организации по ИНН"""
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='inn',
                type=str,
                location=OpenApiParameter.PATH,
                description='ИНН организации (10 или 12 цифр)'
            )
        ],
        responses={
            200: OrganizationBalanceSerializer,
            404: OpenApiResponse(description='Organization not found'),
            500: OpenApiResponse(description='Internal Server Error')
        },
        examples=[
            OpenApiExample(
                'Example response',
                value={
                    "inn": "1234567890",
                    "balance": 145000
                },
                response_only=True
            )
        ],
        description='Получение текущего баланса организации по ИНН'
    )
    def get(self, request, inn, *args, **kwargs):
        try:
            organization = Organization.objects.get(inn=inn)
            serializer = OrganizationBalanceSerializer(organization)
            return Response(serializer.data)
        except Organization.DoesNotExist:
            logger.warning(f"Organization with INN {inn} not found")
            return Response(
                {"error": f"Organization with INN {inn} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error retrieving balance: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )