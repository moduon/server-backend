# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EtlFilterField(models.Model):
    _name = "etl.filter.field"
    _description = "ETL Filter Field"

    process_id = fields.Many2one(comodel_name="etl.process")
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
    field_id = fields.Many2one(comodel_name="etl.field", string="Field")
    value = fields.Char()
    operator = fields.Selection(
        [
            (">", "greater than"),
            ("<", "less than"),
            ("=", "igual"),
            ("like", "contains"),
            ("is null", "is empty"),
            ("is not null", "is not empty"),
            ("not in", "not in"),
        ],
        default=">",
    )
