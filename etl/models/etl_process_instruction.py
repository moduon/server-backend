# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from difflib import SequenceMatcher

from sqlalchemy import text

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class EtlDataMapped(models.Model):
    _name = "etl.process.instruction"
    _description = "Etl Process Instruction"

    process_id = fields.Many2one(
        string="Process",
        comodel_name="etl.process",
        required=True,
    )
    source_table_id = fields.Many2one(
        comodel_name="etl.table",
        string="Source table",
        required=True,
    )
    source_field_id = fields.Many2one(
        string="Source Field",
        comodel_name="etl.field",
    )
    odoo_model_id = fields.Many2one(
        string="Odoo Model",
        comodel_name="ir.model",
    )
    odoo_field_id = fields.Many2one(
        string="Odoo Field",
        comodel_name="ir.model.fields",
        domain="[('model_id', '=', odoo_model_id)]",
    )
    transformation = fields.Selection(
        selection=[
            ("copyvalue", "Use value as is"),
            ("recordmanual", "Search on manual mappings"),
            ("relatedfield", "Add id on related field"),
            ("defaultvalue", "Default value"),
            ("notduplicated", "Not duplicated"),
        ],
        string="What to do with the value",
        required=True,
    )
    transformation_record_manual_name = fields.Char(
        string="Name of manual mappings",
    )
    other_transformation = fields.Text(
        string="Transformation or Cast",
        help="Transformation or Cast to apply \n"
        "to the value of the field when being read from the source.\n"
        "Will be applied before the transformation selected in the previous field.\n",
    )
    related_destination_field_id = fields.Many2one(comodel_name="ir.model.fields")
    related_destination_search_table_id = fields.Many2one(comodel_name="ir.model")
    related_source_field_id = fields.Many2one(comodel_name="etl.field")
    related_source_search_table_id = fields.Many2one(comodel_name="etl.table")
    join_external_field_id = fields.Many2one(comodel_name="etl.field")
    multiples_records = fields.Boolean()
    upgrade_field = fields.Boolean(
        string="This value can be updated or not",
        default=True,
        help="If this is not checked, the value will be ignored.",
    )
    domain = fields.Char()
    where_table = fields.Char(
        string="Filter table condition",
    )

    @api.onchange("odoo_model_id")
    def onchange_odoo_model(self):
        """This method is called when the user
        changes the value of the odoo_model_id field."""
        for rec in self:
            return {
                "domain": {"odoo_field_id": [("model_id", "=", rec.odoo_model_id.id)]}
            }

    @api.onchange("related_destination_search_table_id")
    def onchange_related_model(self):
        """This method is called when the user changes the value
        of the related_destination_search_table_id field."""
        for rec in self:
            return {
                "domain": {
                    "related_destination_field_id": [
                        ("model_id", "=", rec.related_destination_search_table_id.id)
                    ]
                }
            }

    def _transform(self, external_row):  # check_other_transformations
        """this function check if the field has other transformations"""
        self.ensure_one()
        return safe_eval(self.other_transformation, {"object": external_row})

    def get_real_value(self, external_row, engine):
        self.ensure_one()
        if self.other_transformation:
            return self._transform(external_row)

    def get_value_related_source_table(self, rec, engine):
        """this function check if the field has a related
        source search table and if it has, search the data in the source database"""
        result = {}
        result.update({self.odoo_field_id.name: self.related_source_data(rec, engine)})
        return result

    def related_source_data(self, rec, engine):
        """this function search the related data in the source database"""
        val = ""
        filter_sql = self.where_table or ""
        sql = text(
            ("select %s from %s where %s = %s %s")
            % (
                self.related_source_field_id.name,
                self.related_source_search_table_id.name,
                self.join_external_field_id.name,
                str(rec._mapping[self.source_field_id.name]).strip(),
                filter_sql,
            )
        )
        res = engine.execute(sql)
        for row in res:
            if not self.multiples_records:
                return str(row[0])
            val += str(row[0]) + "\n"
        return val

    def get_other_transformations(self, rec):
        """this function check if the field has other transformations"""
        result = {}
        result.update(
            {self.odoo_field_id.name: self.custom_funct(rec, self.other_transformation)}
        )
        return result

    def custom_funct(self, value, func):
        """this function is for custom functions"""
        return safe_eval(func, {"object": value})

    def add_fieldId_for_related_table(self, rec, prcs):
        result = {}
        id_orig = self.env["etl.mapping.record.auto"].search(
            [
                ("process_id", "=", prcs),
                (
                    "external_id",
                    "=",
                    rec._mapping[self.source_table_id.primary_key_id.name],
                ),
                # ('odoo_model_id', '=', self.odoo_model_id.id)
            ]
        )
        if id_orig:
            result.update({self.odoo_field_id.name: id_orig[0].odoo_id})
        else:
            raise Exception(
                ("The related record with id %s dont exist"), str(id_orig[0].odoo_id)
            )
        return result

    def get_value_related_destination_search_table(self, rec):
        """this function check if the field has a related destination
        search table and if it has, search the data in the destination database"""
        result = {}
        vals = False
        if self.related_destination_search_table_id:
            if rec._mapping[self.source_field_id.name]:
                vals = self.env[self.related_destination_search_table_id.model].search(
                    [
                        (
                            self.related_destination_field_id.name,
                            "ilike",
                            rec._mapping[self.source_field_id.name],
                        )
                    ]
                )
                if not vals:
                    vals = self.env[
                        self.related_destination_search_table_id.model
                    ].search([])
            if vals:
                if len(vals) > 1:
                    str_cmp_prc = 0
                    best_id = self.env.ref("etl.state_country_notfound").id
                    for val in vals:
                        sm_res = SequenceMatcher(
                            None,
                            str(val[self.related_destination_field_id.name]).upper(),
                            str(rec._mapping[self.source_field_id.name]).upper(),
                        ).ratio()
                        if sm_res > str_cmp_prc and sm_res > 0.8:
                            str_cmp_prc = sm_res
                            best_id = val.id
                        result.update({self.odoo_field_id.name: best_id})
                else:
                    result.update({self.odoo_field_id.name: vals.id})
        elif not self.related_source_search_table_id:
            result.update({self.odoo_field_id.name: self.transform_field(rec)})
        return result

    def transform_field(self, rec):
        """in this function we can add more transformations"""
        # TODO: Aplicar el casteo de campos (zfill y tal) aquí
        # TODO: probar el _convert_to_write de la clase ir.model.fields
        if not self.source_field_id:
            return ""
        orig = self.source_field_id.field_type
        dest = self.odoo_field_id.ttype
        if orig != dest:
            if orig == "int" and dest == "char":
                return str(rec._mapping[self.source_field_id.name])
            if orig == "str" and dest == "integer":
                return int(rec._mapping[self.source_field_id.name].strip())
        if dest == "char":
            if not rec._mapping[self.source_field_id.name]:
                return ""
            return str(rec._mapping[self.source_field_id.name]).strip()
        return rec._mapping[self.source_field_id.name]

    def get_value_manual_mappings(self, rec):
        """this function search the manual mappings"""
        manual_mappings = self.env["etl.mapping.record.manual"].search(
            "&",
            [
                ("name", "=", self.source_field_id.name),
                ("key", "=", rec._mapping[self.source_field_id.name]),
            ],
        )
        for manual_mapping in manual_mappings:
            return manual_mapping.value
        return ""

    def check_duplicates(self, rec):
        """this function check if the record is duplicated"""
        if self.odoo_field_id:
            if rec._mapping[self.source_field_id.name]:
                value = rec._mapping[self.source_field_id.name]
                if self.other_transformation:
                    value = self.custom_funct(rec, self.other_transformation)
                vals = self.env[self.odoo_model_id.model].search(
                    [
                        (
                            self.odoo_field_id.name,
                            "=",
                            value,
                        )
                    ]
                )
                if vals:
                    return True
        return False
