
from __future__ import unicode_literals
import frappe

def execute():
    from apparelo.apparelo.doctype.lot_creation.custom_scripts import set_custom_fields
    set_custom_fields()