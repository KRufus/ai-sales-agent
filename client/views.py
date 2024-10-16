from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, DestroyAPIView
from rest_framework import status
from .models import Client
from django.db import transaction
from .serializers import ClientSerializer  # Assume you have a ClientSerializer
from rest_framework.permissions import IsAuthenticated
from .tasks import execute_calls_for_user




class ClientList(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ClientSerializer

    def get_queryset(self):
        return Client.objects.filter(created_by=self.request.user)




class ClientDetail(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ClientSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Client.objects.filter(created_by=self.request.user)


    
class ClientDelete(DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ClientSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return Client.objects.filter(created_by=self.request.user)





class ClientCreateOrBulkCreate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data

       
        if isinstance(data, dict):  
            data = [data]

        elif not isinstance(data, list):
            return Response({'error': 'Data must be a list or a single client object'}, status=status.HTTP_400_BAD_REQUEST)

        validated_data = []
        for client_data in data:
            
            if Client.objects.filter(phone_number=client_data.get('phone_number')).exists():
                return Response({'error': f"Phone number {client_data['phone_number']} already exists."}, status=status.HTTP_409_CONFLICT)

           
            serializer = ClientSerializer(data=client_data)
            if not serializer.is_valid():
                return Response({'error': 'Validation failed', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            validated_data.append(serializer.validated_data)

        
        for client_data in validated_data:
            client_data['created_by'] = request.user

        try:
            with transaction.atomic():
               
                clients = Client.objects.bulk_create([Client(**client_data) for client_data in validated_data])

                
                response_serializer = ClientSerializer(clients, many=True)
                return Response({'created_clients': response_serializer.data}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
        
class ExecuteCalls(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        
        created_by_id = request.user.id
        
        print(created_by_id, "created by")

        
        execute_calls_for_user.delay(created_by_id)

        
        return Response({"message": "Call execution started for pending clients."}, status=200)