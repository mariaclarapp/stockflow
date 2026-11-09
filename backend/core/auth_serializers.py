from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class AuthenticatedUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)


class FuncionarioSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nome = serializers.SerializerMethodField()
    username = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)

    def get_nome(self, usuario):
        return usuario.get_full_name() or usuario.username


class FuncionarioCreateSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=150)
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_nome(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Informe o nome do funcionário.")
        return value

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe o usuário de acesso.")
        if get_user_model().objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Este usuário de acesso já está cadastrado.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": "As senhas informadas não coincidem."}
            )
        usuario = get_user_model()(
            username=attrs["username"],
            first_name=attrs["nome"],
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        try:
            validate_password(attrs["password"], user=usuario)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        attrs["usuario"] = usuario
        return attrs

    def create(self, validated_data):
        usuario = validated_data["usuario"]
        usuario.set_password(validated_data["password"])
        usuario.save()
        return usuario


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "A senha atual está incorreta."}
            )
        if attrs["password"] != attrs["password_confirmation"]:
            raise serializers.ValidationError(
                {"password_confirmation": "As senhas informadas não coincidem."}
            )
        try:
            validate_password(attrs["password"], user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs
