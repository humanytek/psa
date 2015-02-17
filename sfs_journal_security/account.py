# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2013 SF Soluciones.
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

from osv import fields, osv
from openerp.tools.translate import _

class account_journal(osv.osv):
    
    _inherit = "account.journal"
    _columns = {
                'user_list': fields.many2many('res.users', 'journal_user_relation',
                                              'journal_id', 'user_id', 'Users')
                }
    
account_journal()

class account_move_line(osv.osv):
    _inherit = "account.move.line"
    
    def create(self, cr, uid, vals, context=None, check=True):
        res =super(account_move_line, self).create(cr, uid, vals, context=context, check=check)
        if vals.get('journal_id'):
            journal_rec = self.pool.get("account.journal").browse(cr, uid, vals.get('journal_id'), context=context)
            if journal_rec.user_list and uid not in [user.id for user in journal_rec.user_list]:
                    raise osv.except_osv(_('Unauthorized User!'), _('You are not allowed to use this Journal'))
        return res
    
    def write(self, cr, uid, ids, vals, context=None, check = True, update_check = True):
        res = super(account_move_line, self).write(cr, uid, ids, vals, context=context, check = check, update_check = update_check)
        if vals.get('journal_id'):
            journal_rec = self.pool.get("account.journal").browse(cr, uid, vals.get('journal_id'), context=context)
            if journal_rec.user_list and uid not in [user.id for user in journal_rec.user_list]:
                    raise osv.except_osv(_('Unauthorized User!'), _('You are not allowed to use this Journal'))
        print res,"4444444444444444444444444444444444"
        return res

account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:-