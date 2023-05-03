# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from sqlalchemy import MetaData, Table

from odoo import models


class BaseExternalDbsource(models.Model):

    _inherit = "base.external.dbsource"

    def load_remote_tables(self):
        engine = self._connection_open_sqlalchemy()
        metadata = MetaData()
        metadata.reflect(bind=engine)
        tables = metadata.tables
        tables_odoo = self.env["etl.table"].search([]).mapped("name")
        for table in tables:
            if table not in tables_odoo:
                self.create_table_and_fields(table, metadata, engine)
        return True

    def create_table_and_fields(self, name, metadata, engine):
        table = Table(name, metadata, autoload=True, autoload_with=engine)
        tbl = self.env["etl.table"].create(
            {
                "name": name,
            }
        )
        columns = table.columns._all_columns
        for column in columns:
            self.env["etl.field"].create(
                {
                    "name": column.name,
                    "table_id": tbl.id,
                    "field_type": column.type.python_type.__name__,
                }
            )

        return columns
