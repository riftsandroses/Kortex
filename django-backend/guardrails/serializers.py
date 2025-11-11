from rest_framework import serializers
from .models import GuardrailApp, CapturedResponse, ModelVersion, TrainingJob

class GuardrailAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardrailApp
        fields = '__all__'
        read_only_fields = ('id','created_at','current_model_version')

class CapturedResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapturedResponse
        fields = ('app', 'request_id', 'prompt', 'response_text', 'meta')

class CapturedResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapturedResponse
        fields = '__all__'
        read_only_fields = ('id','captured_at','evaluated','predicted_label','predicted_score')

class LabelResponseSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=64)
    action = serializers.ChoiceField(choices=[('info','info'),('warning','warning'),('block','block')])

class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = '__all__'
        read_only_fields = ('id','created_at')

class TrainingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingJob
        fields = '__all__'
        read_only_fields = ('id','status','created_at','started_at','finished_at','logs')
