# -*- coding: utf-8 -*-
# Copyright (c) 2019, Aerele Technologies Private Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from six import string_types
from frappe.model.document import Document
from apparelo.apparelo.utils.utils import is_similar_bom
from erpnext import get_default_company, get_default_currency
from erpnext.controllers.item_variant import generate_keyed_value_combinations, get_variant
from apparelo.apparelo.utils.item_utils import get_attr_dict, get_item_attribute_set, create_variants
from apparelo.apparelo.common_scripts import customize_pf_item_code

class Bleaching(Document):
	def on_submit(self):
		create_item_template()

	def create_variants(self, input_item_names, colour=None, item=None, final_process=None):
		new_variants=[]
		input_items = []
		variants = []
		for input_item_name in input_item_names:
			input_items.append(frappe.get_doc('Item', input_item_name))
		for item in input_items:
			yarn_shade_found = False
			attribute_set = get_item_attribute_set(list(map(lambda x: x.attributes,[item])))
			for mapping in self.colour_shade_mapping:
				if mapping.yarn_shade in attribute_set['Yarn Shade']:
					yarn_shade_found = True
					attribute_set['Apparelo Colour'] = [mapping.colour]
					variant = create_variants('Bleached cloth', attribute_set)
					variants.extend(variant)
					variant_doc=frappe.get_doc("Item",variant[0])
					variant_attr = get_attr_dict(variant_doc.attributes)
					new_variants.append(customize_pf_item_code('Bleached Cloth', attribute_set, variant_attr, variant[0]))
			if not yarn_shade_found:
				frappe.throw(_(f"No yarn shade mapping found for {item.item_name}"))
		if len(new_variants)==0:
			new_variants=variants
		return new_variants

	def create_boms(self, input_item_names, variants, colour, attribute_set=None, item_size=None, piece_count=None, final_item=None, final_process=None, dye_bleach_colours=[]):
		input_items = []
		for input_item_name in input_item_names:
			input_items.append(frappe.get_doc('Item', input_item_name))
		boms = []
		for item in input_items:
			attr = get_attr_dict(item.attributes)
			doc_values = self.get_variant_values(attr['Yarn Shade'])
			attr.update(doc_values)
			args_set = generate_keyed_value_combinations(attr)
			for attribute_values in args_set:
				variant = get_variant('Bleached cloth',args=attribute_values)
				if variant in variants:
					bom_for_variant = frappe.get_doc({
						"doctype": "BOM",
						"currency": get_default_currency(),
						"item": variant,
						"company": get_default_company(),
						"quantity": self.output_qty,
						"uom": self.output_uom,
						"items": [
							{
								"item_code": item.name,
								"qty": self.input_qty,
								"uom": self.input_uom,
								"rate": 0.0,
							}
						]
					})
					existing_bom_name = frappe.db.get_value('BOM', {'item': variant, 'docstatus': 1, 'is_active': 1}, 'name')
					if not existing_bom_name:
						bom_for_variant.save()
						bom_for_variant.submit()
						boms.append(bom_for_variant.name)
					else:
						existing_bom = frappe.get_doc('BOM', existing_bom_name)
						similar_diff = is_similar_bom(existing_bom, bom_for_variant)
						if similar_diff:
							boms.append(existing_bom_name)
						else:
							frappe.throw(_("Active BOM with different Materials or qty already exists for the item {0}. Please make this BOM {1} inactive and try again.").format(variant, """<a href="#Form/BOM/{0}">{1}</a>""".format(existing_bom_name, existing_bom_name)))
				else:
					frappe.throw(_("Unexpected error while creating BOM. Expected variant not found in list of supplied variants"))
		return boms

	def get_variant_values(self, yarn_shade):
		attribute_set = {}
		variant_colour = []
		for value in self.colour_shade_mapping:
			if value.yarn_shade in yarn_shade:
				variant_colour.append(value.colour)
		attribute_set['Apparelo Colour'] = variant_colour
		return attribute_set

def create_item_template():
	if not frappe.db.exists("Item","Bleached Cloth"):
		frappe.get_doc({
		"doctype": "Item",
		"item_code": "Bleached Cloth",
		"item_name": "Bleached Cloth",
		"description": "Bleached Cloth",
		"item_group": "Sub Assemblies",
		"stock_uom" : "Kg",
		"has_variants" : "1",
		"variant_based_on" : "Item Attribute",
		"is_sub_contracted_item": "1",
		"attributes" : [
			{
				"attribute" : "Yarn Shade"
			},
			{
				"attribute" : "Yarn Category"
			},
			{
				"attribute" : "Yarn Count"
			},
			{
				"attribute" : "Dia" 
			},
			{
				"attribute" : "Knitting Type"
			},
			{
				"attribute" : "Apparelo Colour"
			}
		]
	}).save()