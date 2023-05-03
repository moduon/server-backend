# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class EtlMappingRecordAuto(models.Model):
    _name = "etl.mapping.record.auto"
    _description = "ETL Mapping Record Auto"

    process_id = fields.Many2one(comodel_name="etl.process")
    source_table_id = fields.Many2one(comodel_name="etl.table")
    primary_key_id = fields.Many2many(comodel_name="etl.field")
    odoo_model_id = fields.Many2one(comodel_name="ir.model")
    odoo_id = fields.Integer(string="Odoo ID")
    external_id = fields.Char(string="External ID")
