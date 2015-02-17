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

from osv import osv

import time
from openerp import tools
from tools.translate import _
from openerp import netsvc
from openerp import release
from openerp import SUPERUSER_ID

class ir_attachment_facturae_mx(osv.osv):
    _inherit = 'ir.attachment.facturae.mx'
    
    def signal_printable(self, cr, uid, ids, context=None):
        try:
            if context is None:
                context = {}
            aids = ''
            msj = ''
            index_pdf = ''
            attachment_obj = self.pool.get('ir.attachment')
            invoice = self.browse(cr, uid, ids)[0].invoice_id
            invoice_obj = self.pool.get('account.invoice')
            type = self.browse(cr, uid, ids)[0].type
            wf_service = netsvc.LocalService("workflow")
            report = invoice_obj.create_report(cr, SUPERUSER_ID, [invoice.id],
                                             "sfs.account.invoice.facturae.webkit.inherit",
                                             invoice.fname_invoice)
            attachment_ids = attachment_obj.search(cr, uid,[
                                                        ('res_model', '=', 'account.invoice'),
                                                        ('res_id', '=', invoice),
                                                        ('datas_fname', '=', invoice.fname_invoice + '.pdf')])
            for attachment in self.browse(cr, uid, attachment_ids, context=context):
                aids = attachment.id #TODO: aids.append( attachment.id ) but without error in last write
                attachment_obj.write(cr, uid, [attachment.id], {
                    'name': invoice.fname_invoice + '.pdf', }, context=context)
            if aids:
                msj = _("Attached Successfully PDF\n")
            else:
                msj = _("Not Attached PDF\n")
            self.write(cr, uid, ids, {
                        'file_pdf': aids or False,
                        'msj': msj,
                        'last_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'file_pdf_index': index_pdf }, context=context)
            wf_service.trg_validate(uid, self._name, ids[0], 'action_printable', cr)
            return True
        except Exception, e:
            self.write(cr, uid, ids, {'msj': tools.ustr(e)}, context=context)
            return False
    
    def signal_send_customer(self, cr, uid, ids, context=None):
        try:
            if context is None:
                context = {}
            attachments = []
            msj = ''
            attach_name = ''
            state = ''
            partner_mail = ''
            user_mail = ''
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            invoice = self.browse(cr, uid, ids)[0].invoice_id
            address_id = self.pool.get('res.partner').address_get(
                cr, uid, [invoice.partner_id.id], ['invoice'])['invoice']
            partner_invoice_address = self.pool.get(
                'res.partner').browse(cr, uid, address_id, context=context)
            type = self.browse(cr, uid, ids)[0].type
            wf_service = netsvc.LocalService("workflow")
            fname_invoice = invoice.fname_invoice and invoice.fname_invoice or ''
            adjuntos = self.pool.get('ir.attachment').search(cr, uid, [(
                'res_model', '=', 'account.invoice'), ('res_id', '=', invoice)])
            subject = 'Invoice '+invoice.number or False
            for attach in self.pool.get('ir.attachment').browse(cr, uid, adjuntos):
                attachments.append(attach.id)
                attach_name += attach.name + ', '
            if release.version >= '7':
                obj_ir_mail_server = self.pool.get('ir.mail_server')
                obj_mail_mail = self.pool.get('mail.mail')
                obj_users = self.pool.get('res.users')
                obj_partner = self.pool.get('res.partner')
                mail_server_id = obj_ir_mail_server.search(cr, uid,
                                                           ['|', ('company_id', '=', company_id), ('company_id', '=', False)], limit = 1, order = 'sequence', context=None)
                if mail_server_id:
                    for smtp_server in obj_ir_mail_server.browse(cr, uid,
                                                                 mail_server_id, context=context):
                        server_name = smtp_server.name
                        smtp = False
                        try:
                            smtp = obj_ir_mail_server.connect(
                                smtp_server.smtp_host, smtp_server.smtp_port,
                                user=smtp_server.smtp_user,
                                password=smtp_server.smtp_pass,
                                encryption=smtp_server.smtp_encryption,
                                smtp_debug=smtp_server.smtp_debug)
                        except Exception, e:
                            raise osv.except_osv(_("Connection test failed!"), _(
                                "Configure outgoing mail server named FacturaE:\n %s") % tools.ustr(e))
                    mail_compose_message_pool = self.pool.get(
                        'mail.compose.message')
                    email_pool = self.pool.get('email.template')
                    tmp_id = email_pool.search(cr, uid, [('model_id.model', '=', 'account.invoice'),
                                                            ('company_id', '=', company_id),
                                                            ('mail_server_id', '=', smtp_server.id),
                                                            ('report_template.report_name', '=', 'sfs.account.invoice.facturae.webkit.inherit')
                                                            ], limit = 1, context=context)
                    if tmp_id:
                        message = mail_compose_message_pool.onchange_template_id(
                            cr, uid, [], template_id=tmp_id[0], composition_mode=None,
                            model='account.invoice', res_id=invoice.id, context=context)
                        mssg = message.get('value', False)
                        user_mail = obj_users.browse(cr, uid, uid, context=None).email
                        partner_id = mssg.get('partner_ids', False)
                        partner_mail = obj_partner.browse(cr, uid, partner_id)[0].email
                        partner_name = obj_partner.browse(cr, uid, partner_id)[0].name
                        if partner_mail:
                            if user_mail:
                                if mssg.get('partner_ids', False) and tmp_id:
                                    mssg['partner_ids'] = [(6, 0, mssg['partner_ids'])]
                                    mssg['attachment_ids'] = [(6, 0, attachments)]
                                    mssg_id = self.pool.get(
                                        'mail.compose.message').create(cr, uid, mssg, context=None)
                                    state = self.pool.get('mail.compose.message').send_mail(
                                        cr, uid, [mssg_id], context=context)
                                    asunto = mssg['subject']
                                    id_mail = obj_mail_mail.search(
                                        cr, uid, [('subject', '=', asunto)])
                                    if id_mail:
                                        for mail in obj_mail_mail.browse(cr, uid, id_mail, context=None):
                                            if mail.state == 'exception':
                                                msj = _(
                                                    '\nNot correct email of the user or customer. Check in Menu Configuración\Tecnico\Email\Emails\n')
                                    else:
                                        msj = _('Email Send Successfully.Attached is sent to %s for Outgoing Mail Server %s') % (partner_mail,server_name)
                            else:
                                raise osv.except_osv(_('Warning'), _('This user\
                                        does not have mail'))
                        else:
                            raise osv.except_osv(_('Warning'), _('The customer %s\
                            does not have mail') % (partner_name))
                    else:
                        raise osv.except_osv(_('Warning'), _('Check that your template is assigned outgoing mail server named %s.\nAlso the field has report_template = Factura Electronica Report.\nTemplate is associated with the same company') % (server_name))
                else:
                    raise osv.except_osv(_('Warning'), _('Not Found\
                    outgoing mail server.Configure the outgoing mail server named "FacturaE"'))
                self.write(cr, uid, ids, {'msj': msj, 'last_date': time.strftime('%Y-%m-%d %H:%M:%S')})
                wf_service.trg_validate(uid, self._name, ids[0], 'action_send_customer', cr)
            return True
        except Exception, e:
            self.write(cr, uid, ids, {'msj': tools.ustr(e)}, context=context)
            return False

ir_attachment_facturae_mx()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
