# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EtlField(models.Model):
    _name = "etl.field"
    _description = "ETL Field"

    table_id = fields.Many2one(
        comodel_name="etl.table",
        string="Table",
        ondelete="cascade",
        required=True,
    )
    name = fields.Char(
        string="Field name",
        required=True,
    )
    field_type = fields.Char(
        string="Field type",
        help="The type of the field in the source table",
    )
