# Copyright 2023 Moduon Team S.L. <info@moduon.team>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from sqlalchemy import MetaData, Table, select
from sqlalchemy.orm import Session

from odoo import fields, models

_logger = logging.getLogger(__name__)


class EtlTable(models.Model):
    _name = "etl.table"
    _description = "ETL Table"

    name = fields.Char(
        string="Name of the table",
        required=True,
    )
    connection_id = fields.Many2one(
        comodel_name="base.external.dbsource",
        string="Connection",
    )
    primary_key_id = fields.Many2one(
        comodel_name="etl.field",
        string="Primary Key",
    )

    def test_conn(self):
        engine = self.connection._connection_open_sqlalchemy()
        metadata = MetaData()
        metadata.reflect(bind=engine)
        # tables = metadata.tables
        session = Session(engine)
        vendedores = Table("VENDEDORES", metadata, autoload=True, autoload_with=engine)
        vendedores_data = select(vendedores)
        result = session.execute(vendedores_data).all()
        return result
