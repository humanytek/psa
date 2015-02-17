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

from openerp import tools
import openerp.addons.decimal_precision as dp

class mrp_ptoc_report(osv.osv):
    _name = 'mrp.ptoc.report'
    _auto = False
    _description = 'Manufacturing Product to Consume Report'
    _columns = {
                'name': fields.many2one('mrp.production', 'Manufacture Order'),
                'qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
                'product_consume_id': fields.many2one('product.product', 'Product to consume'),
                'product_produce_id': fields.many2one('product.product', 'Product to produce'),
                'date_planned': fields.datetime('Date Planned'),
                'delay': fields.integer('Days delay')
                }
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'mrp_ptoc_report')
        cr.execute("""create or replace view mrp_ptoc_report as (SELECT
                            sm.id AS id,
                            mp.id AS name,
                            sm.product_qty AS qty,
                            pp1.id AS product_consume_id,
                            pp2.id AS product_produce_id,
                            mp.date_planned AS date_planned,
                            CASE
                                   WHEN mp.date_planned IS null OR current_date - mp.date_planned::date < 0 THEN 0
                                    ELSE current_date - mp.date_planned::date END AS delay
                        FROM mrp_production_move_ids mpm
                        LEFT JOIN mrp_production mp ON mp.id = mpm.production_id
                        LEFT JOIN stock_move sm ON sm.id = mpm.move_id
                        LEFT JOIN product_product pp1 ON pp1.id = sm.product_id
                        LEFT JOIN product_product pp2 ON pp2.id = mp.product_id
                        WHERE mp.state = 'in_production' and sm.state not in ('done', 'cancel'))
        """)
        
mrp_ptoc_report()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
