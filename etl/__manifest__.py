# Copyright 2023 Moduon - Andrea Cattalani
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl
{
    "name": "ETL",
    "summary": "Connect and import data in Odoo",
    "version": "16.0.1.0.0",
    "category": "Server",
    "website": "https://github.com/OCA/server-backend",
    "author": "Moduon, Odoo Community Association (OCA)",
    "maintainers": ["shide", "Yajo", "anddago78"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "external_dependencies": {"python": ["sqlalchemy"]},
    "depends": [
        "base_external_dbsource_sqlite",
    ],
    "data": [
        "views/etl_field_views.xml",
        "views/etl_filter_fields_views.xml",
        "views/etl_process_instruction_views.xml",
        "views/etl_process_views.xml",
        "views/etl_table_views.xml",
        "views/etl_records_mapping_auto_views.xml",
        "views/etl_records_mapping_manual_views.xml",
        "views/menu_view.xml",
        "views/base_external_dbsource.xml",
        "security/base_user_role.xml",
        "data/data.xml",
    ],
}
