# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from sqlalchemy import MetaData, Table, select, text
from sqlalchemy.orm import Session

from odoo import fields, models


class ETLProcess(models.Model):
    _name = "etl.process"
    _description = "ETL Process"

    name = fields.Char(
        string="Name of the process",
    )
    sequence = fields.Integer(
        default=999,
    )
    odoo_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Oodo model",
        help="This process will create recrods of this model",
    )
    related_process_ids = fields.Many2one(
        comodel_name="etl.process",
        string="Related process",
        help="This processes will be fetched too when checking if the"
        "record is already created",
    )
    data_mapped_ids = fields.One2many(
        comodel_name="etl.process.instruction",
        inverse_name="process_id",
        string="Instructions",
    )
    filter_fields_ids = fields.Many2many(
        comodel_name="etl.filter.field", string="Filter Fields"
    )
    order = fields.Integer()

    def sincronize_data(self):
        """This is a principal function to sincronize data"""
        tables = self.data_mapped_ids.source_table_id.mapped("name")
        for table in tables:
            tbl = self.env["etl.table"].search([("name", "=", table)])
            engine = tbl.connection_id._connection_open_sqlalchemy()
            metadata = MetaData()
            metadata.reflect(bind=engine)
            session = Session(engine)
            table_obj = Table(table, metadata, autoload_with=engine)
            where_clause = self.prepare_where_clause(tbl)
            table_data = select(table_obj).where(where_clause)
            result_data = session.execute(table_data).fetchmany(50)
            instructions = self.data_mapped_ids.filtered(
                lambda x: x.source_table_id.name == table
            )
            for rec in result_data:
                data_to_update = {}
                for instruction in instructions:
                    if instruction.transformation == "notduplicated":
                        dup = instruction.check_duplicates(rec)
                        if dup:
                            data_to_update.update({"duplicate": dup})
                    if instruction.transformation == "copyvalue":
                        data_to_update.update(
                            {
                                instruction.odoo_field_id.name: instruction.transform_field(
                                    rec
                                )
                            }
                        )

                    if instruction.transformation == "recordmanual":
                        res = instruction.get_value_manual_mappings(rec)
                        data_to_update.update(res)
                    if (
                        instruction.related_source_search_table_id
                        and instruction.transformation == "copyvalue"
                    ):
                        res_1 = instruction.get_value_related_source_table(rec, engine)
                        data_to_update.update(res_1)
                    if (
                        instruction.related_destination_search_table_id
                        and instruction.transformation == "copyvalue"
                    ):
                        res_2 = instruction.get_value_related_destination_search_table(
                            rec
                        )
                        data_to_update.update(res_2)
                    if instruction.other_transformation:
                        res_3 = instruction.get_other_transformations(rec)
                        data_to_update.update(res_3)
                    if (
                        self.odoo_model_id
                        and instruction.transformation == "relatedfield"
                    ):
                        res_4 = instruction.add_fieldId_for_related_table(
                            rec, self.related_process_ids.id
                        )
                        data_to_update.update(res_4)
                self.save_record(rec, instruction, data_to_update)
            tbl.connection_id._connection_close_sqlalchemy(engine)
        return True

    def prepare_where_clause(self, tbl):
        where_clause = ""
        for filter_field in self.filter_fields_ids.filtered(
            lambda x: x.table_id == tbl and x.process_id == self
        ):
            if filter_field.field_id.field_type == "str":
                if filter_field.operator == "like":
                    filter_field.value = "'%%%s%%'" % filter_field.value
                elif filter_field.operator == "not in":
                    filter_field.value = "%s" % filter_field.value
                # elif filter_field.value:
                #    filter_field.value = "'%s'" % filter_field.value
            if not filter_field.value:
                filter_field.value = ""
            if where_clause:
                where_clause += " and "
            where_clause = (" %(table)s.%(field)s %(operator)s %(value)s ") % (
                {
                    "table": filter_field.field_id.table_id.name,
                    "field": filter_field.field_id.name,
                    "operator": filter_field.operator,
                    "value": filter_field.value,
                }
            )
        return text(where_clause)

    def _get_open_connections_by_table(self):
        """Devuelve un diccionario con el mapeo de
        las tablas y sus conexiones ya abiertas"""
        tables = self.env["etl.table"].browse()
        for process in self:
            for process_instruction in process.data_mapped_ids:
                tables |= process_instruction.source_field_id.table_id
                tables |= process_instruction.related_source_search_table_id

        result = {}
        for table in tables:
            engine = table.connection_id._connection_open_sqlalchemy()
            metadata = MetaData()
            metadata.reflect(bind=engine)
            result[table] = {
                "table": Table(table.name, metadata, autoload_with=engine),
                "engine": engine,
                "session": Session(engine),
                "instructions": self.data_mapped_ids.filtered(
                    lambda i: i.source_field_id.table_id == table
                ),
            }
        return result

    def save_record(self, rec, field, crt):
        """this function save the record mapped in odoo and check if
        the record has to be created or only updated"""
        self.ensure_one()
        emra_model = self.env["etl.mapping.record.auto"]
        # TODO: Como sacar la clave primaria del proceso
        # (sin utilizar un instruction en concreto)
        id_pk = field.source_table_id.primary_key_id.name
        odoo_model = self.env[self.odoo_model_id.model]
        external_str_id = str(rec._mapping[id_pk])

        existing_record = emra_model.search(
            [
                "&",
                # Le pasamos el proceso actual y los que ha especificado
                # en related_process_ids (si hay alguno más)
                ("process_id", "=", self.id),
                ("external_id", "=", external_str_id),
            ]
        )
        if existing_record:
            fields_to_not_update = self.data_mapped_ids.filtered(
                lambda i: not i.upgrade_field
            ).mapped("odoo_field_id.name")
            for fname in fields_to_not_update:
                crt.pop(fname, None)
            res = odoo_model.browse(existing_record.odoo_id).write(
                odoo_model._convert_to_write(crt)
            )
        else:
            # self.add_fieldId_for_related_table(field, rec, crt)
            if "duplicate" in crt:
                return True
            prepare_values = odoo_model._convert_to_write(crt)
            res = odoo_model.create(prepare_values)
            emra_model.create(
                {
                    "process_id": self.id,
                    # "source_table_id": field.source_table_id.id,
                    "odoo_model_id": self.odoo_model_id.id,
                    "odoo_id": res.id,
                    "external_id": external_str_id,
                }
            )
