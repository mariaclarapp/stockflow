from django.test import TestCase

from .models import Ups


class UpsModelTests(TestCase):
    def test_consolidation_configuration_defaults_to_enabled(self):
        ups = Ups.objects.create(codigo_gmus="UPS-TESTE", nome="UPS TESTE")

        self.assertTrue(ups.participa_competencia)
        self.assertTrue(ups.compoe_estoque_convencional)
