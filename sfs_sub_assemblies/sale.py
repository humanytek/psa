# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 SF Soluciones.
#    (http://www.sfsoluciones.com)
#    contacto@sfsoluciones.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

from lxml import etree
import openerp.addons.decimal_precision as dp
from tools.translate import _

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    
    def onchange_subassembly(self, cr, uid, ids, product_id, assembly_line_ids, context=None):
        res = {}
        return res
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False,
            flag=False, context=None):
        if context is None:
            context = {}
        del_line = []
        pricelist_pool = self.pool.get('product.pricelist')
        assembly_line_pool = self.pool.get('sale.assembly.line')
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty, uom, qty_uos,
                                                             uos, name, partner_id, lang, update_tax, date_order,
                                                             packaging, fiscal_position, flag, context=context)
        if product:
            product_pool = self.pool.get('product.product')
            product_obj = product_pool.browse(cr, uid, product, context=context)
            if product_obj.contain_sub_assemblies and product_obj.supply_method == 'produce':
                res['value']['contain_sub_assemblies'] = True
            else:
                res['value']['contain_sub_assemblies'] = False
        if context.get('product_changed', False):
            assembly_bom_ids = context.get('assembly_bom_ids', [])
            assembly_line_ids = context.get('assembly_line_ids', [])
            bom_data = []
            for bom in assembly_bom_ids:
                bom_ids = bom[2] or []
                for bom_id in bom_ids:
                    bom_data.append((3, bom_id))
            line_data = []
            for assembly_line_data in assembly_line_ids:
                if not assembly_line_data[2] and assembly_line_data[0] == 4:
                        assembly_line_id = assembly_line_data[1]
                        if assembly_line_id:
                            line_data.append((2, assembly_line_id))
            res['value'].update({'assembly_bom_ids': [], 'assembly_line_ids': line_data})
        if context.get('assembly_bom_ids', False) and not context.get('product_changed', False):
            assembly_bom_ids = context.get('assembly_bom_ids', [])
            assembly_line_ids = context.get('assembly_line_ids', [])
            for assembly_line_data in assembly_line_ids:
                if not assembly_line_data[2]:
                    assembly_line_id = assembly_line_data[1]
                    if assembly_line_id:
                        del_line.append((2, assembly_line_id))
            result = self.onchange_assembly_bom_ids(cr, uid, ids, assembly_bom_ids, [], uom,
                                                    qty, fiscal_position, pricelist, partner_id, date_order,
                                                    context)
            if del_line:
                if not result['value'].get('assembly_line_ids', False):
                    result['value']['assembly_line_ids'] = []
                result['value']['assembly_line_ids'].extend(del_line)
            if res.get('warning', False) and result.get('warning', False):
                res['warning']['message'] += "\n" + result['warning']['message']
            elif not res.get('warning', False) and result.get('warning', False):
                res['warning'] = result['warning']
            res['value'].update(result['value'])
        return res
    
    def get_bom_product_details(self, cr, uid, bom_ids, uom_id, qty, fpos, pricelist, partner_id,
                                date_order, context=None):
        if context is None:
            context = {}
        warning = ""
        res = []
        bom_pool = self.pool.get('mrp.bom')
        uom_pool = self.pool.get('product.uom')
        product_pool = self.pool.get('product.product')
        fiscal_position_pool = self.pool.get('account.fiscal.position')
        pricelist_pool = self.pool.get('product.pricelist')
        move_pool = self.pool.get('stock.move')
        fpos = fpos and fiscal_position_pool.browse(cr, uid, fpos) or False
        for bom_id in bom_ids:
            bom_obj = bom_pool.browse(cr, uid, bom_id, context=context)
            bom_uom_id = bom_obj.product_uom.id
            if uom_id != bom_uom_id:
                factor = uom_pool._compute_qty(cr, uid, uom_id, qty or 0.00, bom_uom_id)
            else:
                factor = qty
            bom_datas = bom_pool._bom_explode(cr, uid, bom_obj, factor)
            for bom_data in bom_datas:
                for bom_product_data in bom_data:
                    product_id = bom_product_data.get('product_id', False)
                    price = 0.00
                    price = pricelist_pool.price_get(cr, uid, [pricelist],
                                                     product_id, qty or 1.0, partner_id, {
                                                                                       'uom': uom_id,
                                                                                       'date': date_order,
                                                                                        })[pricelist]
                    context['uom'] = bom_product_data.get('product_uom', False)
                    product_obj = product_pool.browse(cr, uid, product_id, context=context)
                    qty_available = product_obj.qty_available or 0.00
                    if qty_available < bom_product_data.get('product_qty', 1.00):
                        warning += (warning and "\n") + _("Product %s out of stock")%(product_obj.name)
                        move_ids = move_pool.search(cr, uid, [('state', 'not in', ['draft', 'cancel', 'done']),
                                                              ('picking_id.type', '=', 'in'),
                                                              ('product_id', '=', product_obj.id)],
                                                    order='date_expected', limit=1,context=context)
                        if move_ids:
                            move_obj = move_pool.browse(cr, uid, move_ids[0], context=context)
                            warning += _("\nThere is an incoming shipment of %s %s on %s")%(move_obj.product_qty,
                                                                                            move_obj.product_uom.name,
                                                                                            str(move_obj.date_expected))
                        else:
                            warning += _("\n This product has no incoming shipment")
                    tax_ids = fiscal_position_pool.map_tax(cr, uid, fpos, product_obj.taxes_id)
                    assembly_line_data = {
                                          'product_id': bom_product_data.get('product_id', False),
                                          'description': bom_product_data.get('name', ''),
                                          'product_uom_qty': bom_product_data.get('product_qty', 1.00),
                                          'product_uom_id': bom_product_data.get('product_uom', False),
                                          'tax_ids': [(6, 0, tax_ids)],
                                          'price_unit': price or 0.00,
                                          'bom_id': bom_id
                                          }
                    res.append((0, 0, assembly_line_data))
        return res, warning
    
    def onchange_assembly_bom_ids(self, cr, uid, ids, assembly_bom_ids, assembly_line_ids, uom_id, qty,
                                  fpos, pricelist, partner_id, date_order, context=None):
        res = {'value': {}}
        ass_warning = ""
        assembly_line_pool = self.pool.get('sale.assembly.line')
        if assembly_bom_ids:
            bom_ids = []
            for assembly_bom in assembly_bom_ids:
                bom_ids = assembly_bom[2]
            assembly_line_data = []
            existing_bom_ids = []
            saved_line_data = {}
            assembly_line_index_data = {}
            for assembly_line in assembly_line_ids:
                if not assembly_line[2]:
                    line_id = assembly_line[1]
                    line_obj = assembly_line_pool.browse(cr, uid, line_id, context=context)
                    bom_id = line_obj.bom_id.id
                    assembly_line_data.append(assembly_line)
                    if not assembly_line_index_data.get(bom_id, False):
                        assembly_line_index_data[bom_id] = []
                    if not saved_line_data.get(bom_id, False):
                        saved_line_data[bom_id] = []
                    assembly_line_index_data[bom_id].append(len(assembly_line_data) - 1)
                    saved_line_data[bom_id].append(line_id)
                    existing_bom_ids.append(bom_id)
                elif isinstance(assembly_line[2], dict):
                    bom_id = assembly_line[2].get('bom_id', False)
                    assembly_line_data.append(assembly_line)
                    if not assembly_line_index_data.get(bom_id, False):
                        assembly_line_index_data[bom_id] = []
                    assembly_line_index_data[bom_id].append(len(assembly_line_data) - 1)
                    existing_bom_ids.append(bom_id)
            new_bom_ids = list(set(bom_ids) - set(existing_bom_ids))
            del_bom_ids = list(set(existing_bom_ids) - set(bom_ids))
            if new_bom_ids or del_bom_ids:
                assembly_lines = []
                if new_bom_ids:
                    assembly_lines, ass_warning = self.get_bom_product_details(cr, uid, new_bom_ids, uom_id, qty, fpos,
                                                                               pricelist, partner_id,
                                                                               date_order, context=context)
                for del_bom_id in del_bom_ids:
                    del_bom_index = assembly_line_index_data.get(del_bom_id, [])
                    assembly_line_data = [v for i,v in enumerate(assembly_line_data) if i not in frozenset(del_bom_index)]
                    del_line_ids = saved_line_data.get(del_bom_id, [])
                    for del_line_id in del_line_ids:
                        assembly_lines.append((2, del_line_id))
                assembly_lines.extend(assembly_line_data)
                res['value'].update({
                                     'assembly_line_ids': assembly_lines
                                     })
        if ass_warning:
            warning = {
                       'title': _('Product out of Stock !!'),
                       'message' : ass_warning
                       }
            res.update({'warning': warning})
        return res
    
    def _get_assembly_line_order(self, cr, uid, ids, context=None):
        res = []
        assembly_line_pool = self.pool.get('sale.assembly.line')
        try:
            for assembly_line_obj in assembly_line_pool.browse(cr, uid, ids, context=context):
                res.append(assembly_line_obj.sale_line_id.id)
        except:
            pass
        return res
    
    def _amount_assembly_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_ids, line.price_unit,
                                                          line.product_uom_qty, line.product_id,
                                                          line.sale_line_id.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val

    def _assembly_amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'assembly_amount_untaxed': 0.0,
                'assembly_amount_tax': 0.0,
                'assembly_amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.order_id.pricelist_id.currency_id
            for line in order.assembly_line_ids:
                val1 += line.amount_total
                val += self._amount_assembly_line_tax(cr, uid, line, context=context)
            res[order.id]['assembly_amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['assembly_amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['assembly_amount_total'] = res[order.id]['assembly_amount_untaxed'] + \
                                                            res[order.id]['assembly_amount_tax']
        return res
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, line.product_uom_qty, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
            subassembly_total = line.assembly_amount_untaxed or 0.00
            res[line.id] += subassembly_total
        return res
    
    
    _columns = {
                'contain_sub_assemblies': fields.boolean('Can contain Sub Assemblies'),
                'assembly_bom_ids': fields.many2many('mrp.bom', 'bom_sale_rel', 'sale_line_id', 'bom_id', 'Sub Assembly'),
                'assembly_line_ids': fields.one2many('sale.assembly.line', 'sale_line_id', 'Sub Assembly Products'),
                'assembly_amount_untaxed': fields.function(_assembly_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                        store={
                            'sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['assembly_line_ids'], 10),
                            'sale.assembly.line': (_get_assembly_line_order, ['price_unit', 'tax_ids', 'product_uom_qty'], 10),
                        },
                        multi='assembly_sums', help="The amount without tax.", track_visibility='always'),
                'assembly_amount_tax': fields.function(_assembly_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
                        store={
                            'sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['assembly_line_ids'], 10),
                            'sale.assembly.line': (_get_assembly_line_order, ['price_unit', 'tax_ids', 'product_uom_qty'], 10),
                        },
                        multi='assembly_sums', help="Total tax.", track_visibility='always'),
                'assembly_amount_total': fields.function(_assembly_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                        store={
                            'sale.order.line': (lambda self, cr, uid, ids, c={}: ids, ['assembly_line_ids'], 10),
                            'sale.assembly.line': (_get_assembly_line_order, ['price_unit', 'tax_ids', 'product_uom_qty'], 10),
                        },
                        multi='assembly_sums', help="The amount with tax.", track_visibility='always'),
                'price_subtotal': fields.function(_amount_line, string='Subtotal',
                                                  digits_compute= dp.get_precision('Account')),
                }
    
    def button_dummy(self, cr, uid, ids, context=None):
        return True
    
sale_order_line()

class sale_order(osv.osv):
    _inherit = 'sale.order'
    
    def fields_view_get(self, cr, user, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        res = super(sale_order, self).fields_view_get(cr, user, view_id, view_type, context=context,
                                                      toolbar=toolbar, submenu=submenu)
        if view_type == 'form' and res.get('fields', False) and res['fields'].get('order_line', False) and \
                        res['fields']['order_line'].get('views', False) and \
                        res['fields']['order_line']['views'].get('form', False):
            order_line_arch = res['fields']['order_line']['views']['form']['arch']
            doc = etree.XML(order_line_arch)
            content_element = doc.xpath("//form/group")
            order_line_page_node = doc.xpath("//page[@string='Order Line']")
            for page_node in order_line_page_node:
                for node in content_element:
                    doc.remove(node)
                    node_data = etree.tostring(node)
                    page_node.append(etree.fromstring(str(node_data)))
            res['fields']['order_line']['views']['form']['arch'] = etree.tostring(doc)
        return res
    
    def _get_assembly_order(self, cr, uid, ids, context=None):
        res = []
        assembly_line_pool = self.pool.get('sale.assembly.line')
        try:
            for assembly_line_obj in assembly_line_pool.browse(cr, uid, ids, context=context):
                if assembly_line_obj.sale_line_id:
                    res.append(assembly_line_obj.sale_line_id.order_id.id)
        except:
            pass
        return res
    
    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
    
    def _amount_ass_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_ids, line.price_unit, line.product_uom_qty, line.product_id, line.sale_line_id.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val
    
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = super(sale_order, self)._amount_all(cr, uid, ids, name, args, context=context)
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for order in self.browse(cr, uid, ids, context=context):
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val = val1 = 0.00
                for ass_line in line.assembly_line_ids:
                    ass_line_tax_amount = self._amount_ass_line_tax(cr, uid, ass_line, context=context)
                    val += ass_line_tax_amount
                    val1 += ass_line.price_unit * ass_line.product_uom_qty
                val = cur_obj.round(cr, uid, cur, val)
                val1 = cur_obj.round(cr, uid, cur, val1)
                res[order.id]['amount_tax'] += val
                res[order.id]['amount_untaxed'] += val1
                res[order.id]['amount_total'] += val + val1
        return res
    
    _columns = {
                'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                        'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty',
                                                         'assembly_line_ids', 'assembly_amount_untaxed',
                                                         'assembly_amount_tax', 'assembly_amount_total'], 10),
                        'sale.assembly.line': (_get_assembly_order, ['price_unit', 'tax_id', 'product_uom_qty'], 10),
                    },
                    multi='sums', help="The amount without tax.", track_visibility='always'),
                'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                        'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty',
                                                         'assembly_line_ids', 'assembly_amount_untaxed',
                                                         'assembly_amount_tax', 'assembly_amount_total'], 10),
                        'sale.assembly.line': (_get_assembly_order, ['price_unit', 'tax_id', 'product_uom_qty'], 10),
                    },
                    multi='sums', help="The tax amount."),
                'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
                    store={
                        'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                        'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty',
                                                         'assembly_line_ids', 'assembly_amount_untaxed',
                                                         'assembly_amount_tax', 'assembly_amount_total'], 10),
                        'sale.assembly.line': (_get_assembly_order, ['price_unit', 'tax_id', 'product_uom_qty'], 10),
                    },
                    multi='sums', help="The total amount."),
                }
    
    def print_quotation(self, cr, uid, ids, context=None):
        res = super(sale_order, self).print_quotation(cr, uid, ids, context=context)
        res['report_name'] = 'sfs.sale.order.inherit'
        return res

sale_order()

class sale_assembly_line(osv.osv):
    _name = 'sale.assembly.line'
    _description = 'Model to hold assembly line in sale'
    
    def onchange_bom_id(self, cr, uid, ids, product_id, bom_id, uom_id, qty, context=None):
        res = {}
        return res
    
    def _amount_line(self, cr, uid, ids, name, args, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit or 0.00
            taxes = tax_obj.compute_all(cr, uid, line.tax_ids, price, line.product_uom_qty, line.product_id,
                                        line.sale_line_id.order_id.partner_id)
            cur = line.sale_line_id.order_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res
    
    def onchange_product_id(self,cr, uid, ids, product_id,context=None):
        res = {}
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            vals = {
                    'description': product.name,
                    'product_uom_id': product.uom_id and product.uom_id.id or False,
                    'price_unit': product.list_price
                    }
            res['value'] = vals
        return res
    
    _columns = {
                'bom_id': fields.many2one('mrp.bom', 'BOM'),
                'product_id': fields.many2one('product.product', 'Product'),
                'description': fields.char('Description', size=128),
                'product_uom_qty': fields.float('Quantity', digits_compute= dp.get_precision('Product UoS')),
                'product_uom_id': fields.many2one('product.uom', 'Unit of Measure'),
                'tax_ids': fields.many2many('account.tax', 'assembly_tax_rel', 'assembly_line_id',
                                           'tax_id', 'Taxes'),
                'price_unit': fields.float('Price Unit', digits_compute= dp.get_precision('Product UoS')),
                'amount_total': fields.function(_amount_line, string='Subtotal',
                                                digits_compute= dp.get_precision('Account')),
                'sale_line_id': fields.many2one('sale.order.line', 'Sale order line')
                }
    
sale_assembly_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
