# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EtlMappingRecordManual(models.Model):
    _name = "etl.mapping.record.manual"
    _description = "ETL Mapping Record Manual"

    name = fields.Char(
        string="Mapping name",
        required=True,
        help="Name of the mapping record.\n"
        "Use a name to easily find with a domain on ETL Process Instruction.",
    )
    key = fields.Char(
        required=True,
    )
    value = fields.Char(
        required=True,
    )

    def get_dict_from_name(self, name):
        """Devuelve un diccionario de clave:valor a partir de un dominio.
        Ej.: {"Zaragoza": "42"}
        """
        all_possible_mappings = self.search([("name", "=", name)])
        return {rmm.key: rmm.value for rmm in all_possible_mappings}
