from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db.models import ProtectedError
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, BasePermission, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_serializers import (
    AuthenticatedUserSerializer,
    FuncionarioCreateSerializer,
    FuncionarioSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
)


class IsSuperUser(BasePermission):
    message = "Somente o superusuário pode gerenciar funcionários."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_superuser
        )


class CsrfCookieAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        SessionAuthentication().enforce_csrf(request)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request=request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active or not user.is_staff:
            return Response(
                {"detail": "Não foi possível autenticar com as credenciais informadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        login(request, user)
        return Response(
            {"user": AuthenticatedUserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response(AuthenticatedUserSerializer(request.user).data)


class PasswordChangeAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["password"])
        request.user.save(update_fields=["password"])
        login(request, request.user)
        return Response({"detail": "Senha alterada com sucesso."})


class FuncionarioListCreateAPIView(APIView):
    permission_classes = [IsSuperUser]

    def get(self, request):
        funcionarios = (
            get_user_model()
            .objects.filter(is_staff=True, is_superuser=False)
            .order_by("first_name", "username")
        )
        return Response(FuncionarioSerializer(funcionarios, many=True).data)

    def post(self, request):
        serializer = FuncionarioCreateSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            first_error = next(iter(errors.values()), ["Dados inválidos."])
            if isinstance(first_error, dict):
                first_error = next(iter(first_error.values()), ["Dados inválidos."])
            if isinstance(first_error, (list, tuple)):
                first_error = first_error[0] if first_error else "Dados inválidos."
            return Response(
                {**errors, "erro": str(first_error)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        funcionario = serializer.save()
        return Response(
            FuncionarioSerializer(funcionario).data,
            status=status.HTTP_201_CREATED,
        )


class FuncionarioDetailAPIView(APIView):
    permission_classes = [IsSuperUser]

    def get_object(self, pk):
        return get_user_model().objects.get(
            pk=pk,
            is_staff=True,
            is_superuser=False,
        )

    def patch(self, request, pk):
        try:
            funcionario = self.get_object(pk)
        except get_user_model().DoesNotExist:
            return Response({"detail": "Funcionário não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        if not isinstance(request.data.get("is_active"), bool):
            return Response(
                {"detail": "Informe is_active como booleano."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        funcionario.is_active = request.data["is_active"]
        funcionario.save(update_fields=["is_active"])
        return Response(FuncionarioSerializer(funcionario).data)

    def delete(self, request, pk):
        try:
            funcionario = self.get_object(pk)
        except get_user_model().DoesNotExist:
            return Response({"detail": "Funcionário não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        try:
            funcionario.delete()
        except ProtectedError:
            return Response(
                {"detail": "Este funcionário possui histórico e deve ser desativado."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
