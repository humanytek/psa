# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.safe_eval import safe_eval
from openerp.tools.translate import _

from datetime import date, datetime, timedelta

import logging

_logger = logging.getLogger(__name__)


class gamification_goal_type(osv.Model):
    """Goal type definition

    A goal type defining a way to set an objective and evaluate it
    Each module wanting to be able to set goals to the users needs to create
    a new gamification_goal_type
    """
    _name = 'gamification.goal.type'
    _description = 'Gamification goal type'
    _order = 'sequence'

    def _get_suffix(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.suffix and not goal.monetary:
                res[goal.id] = goal.suffix
            elif goal.monetary:
                # use the current user's company currency
                user = self.pool.get('res.users').browse(cr, uid, uid, context)
                if goal.suffix:
                    res[goal.id] = "%s %s" % (user.company_id.currency_id.symbol, goal.suffix)
                else:
                    res[goal.id] = user.company_id.currency_id.symbol
            else:
                res[goal.id] = ""
        return res
    
    def on_change_field(self, cr, uid, ids, field_date_name, model_id, context=None):
        res = {}
        model_obj = self.pool.get('ir.model').browse(cr, uid, model_id, context)
        date_field = 0
        i = 0
        for s in field_date_name.split('.'):
            i = i+1
            for field_rec in model_obj.field_id:
                if field_rec.name == s and field_rec.ttype == 'many2one':
                    new_model_id = self.pool.get('ir.model').search(cr, uid, 
                                                                    [('model','=',field_rec.relation)], context)[0]
                    model_obj = self.pool.get('ir.model').browse(cr, uid, new_model_id, context)
                if field_rec.name == s and field_rec.ttype == 'date' and i == len(field_date_name.split('.')):
                    date_field = 1
        if date_field != 1:
            raise osv.except_osv(_('Field Error'),_("The Field Provided is not of date Format or it is not present"))
        return res
    
    _columns = {
        'name': fields.char('Goal Type', required=True, translate=True),
        'description': fields.text('Goal Description'),
        'monetary': fields.boolean('Monetary Value', help="The target and current value are defined in the company currency."),
        'suffix': fields.char('Suffix', help="The unit of the target and current values", translate=True),
        'full_suffix': fields.function(_get_suffix, type="char", string="Full Suffix", help="The currency and suffix field"),
        'computation_mode': fields.selection([
                ('manually', 'Recorded manually'),
                ('count', 'Automatic: number of records'),
                ('sum', 'Automatic: sum on a field'),
                ('python', 'Automatic: execute a specific Python code'),
            ],
            string="Computation Mode",
            help="Defined how will be computed the goals. The result of the operation will be stored in the field 'Current'.",
            required=True),
        'display_mode': fields.selection([
                ('progress', 'Progressive (using numerical values)'),
                ('checkbox', 'Checkbox (done or not-done)'),
            ],
            string="Displayed as", required=True),
        'model_id': fields.many2one('ir.model',
            string='Model',
            help='The model object for the field to evaluate'),
        'field_id': fields.many2one('ir.model.fields',
            string='Field to Sum',
            help='The field containing the value to evaluate'),
        'field_date_name': fields.char('Date Field', size=256,
            help='The date to use for the time period evaluated'),
                #TODO: actually it would be better to use 'user.id' in the domain definition, because it means user is a browse record and it's more flexible (i can do '[(country_id,=,user.partner_id.country_id.id)])

        'domain': fields.char("Filter Domain",
            help="Technical filters rules to apply. Use 'user.id' (without marks) to limit the search to the evaluated user.",
            required=True),
        'compute_code': fields.char('Compute Code',
            help="The name of the python method that will be executed to compute the current value. See the file gamification/goal_type_data.py for examples."),
        'condition': fields.selection([
                ('higher', 'The higher the better'),
                ('lower', 'The lower the better')
            ],
            string='Goal Performance',
            help='A goal is considered as completed when the current value is compared to the value to reach',
            required=True),
        'sequence': fields.integer('Sequence', help='Sequence number for ordering', required=True),
        'action_id': fields.many2one('ir.actions.act_window', string="Action",
            help="The action that will be called to update the goal value."),
        'res_id_field': fields.char("ID Field of user",
            help="The field name on the user profile (res.users) containing the value for res_id for action.")
    }

    _defaults = {
        'sequence': 1,
        'condition': 'higher',
        'computation_mode': 'manually',
        'domain': "[]",
        'monetary': False,
        'display_mode': 'progress',
    }


class gamification_goal(osv.Model):
    """Goal instance for a user

    An individual goal for a user on a specified time period"""

    _name = 'gamification.goal'
    _description = 'Gamification goal instance'
    _inherit = 'mail.thread'

    def _get_completeness(self, cr, uid, ids, field_name, arg, context=None):
        """Return the percentage of completeness of the goal, between 0 and 100"""
        res = dict.fromkeys(ids, 0.0)
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.type_condition == 'higher' and goal.current > 0:
                res[goal.id] = min(100, round(100.0 * goal.current / goal.target_goal, 2))
            elif goal.current < goal.target_goal:
                # a goal 'lower than' has only two values possible: 0 or 100%
                res[goal.id] = 100.0
        return res

    def on_change_type_id(self, cr, uid, ids, type_id=False, context=None):
        goal_type = self.pool.get('gamification.goal.type')
        if not type_id:
            return {'value': {'type_id': False}}
        goal_type = goal_type.browse(cr, uid, type_id, context=context)
        return {'value': {'computation_mode': goal_type.computation_mode, 'type_condition': goal_type.condition}}

    _columns = {
        'type_id': fields.many2one('gamification.goal.type', string='Goal Type', required=True, ondelete="cascade"),
        'user_id': fields.many2one('res.users', string='User', required=True),
        'planline_id': fields.many2one('gamification.goal.planline', string='Goal Planline', ondelete="cascade"),
        'plan_id': fields.related('planline_id', 'plan_id',
            string="Plan",
            type='many2one',
            relation='gamification.goal.plan',
            store=True),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),  # no start and end = always active
        'target_goal': fields.float('To Reach',
            required=True,
            track_visibility='always'),  # no goal = global index
        'current': fields.float('Current Value', required=True, track_visibility='always'),
        'completeness': fields.function(_get_completeness, type='float', string='Completeness'),
        'state': fields.selection([
                ('draft', 'Draft'),
                ('inprogress', 'In progress'),
                ('inprogress_update', 'In progress (to update)'),
                ('reached', 'Reached'),
                ('failed', 'Failed'),
                ('canceled', 'Canceled'),
            ],
            string='State',
            required=True,
            track_visibility='always'),

        'computation_mode': fields.related('type_id', 'computation_mode', type='char', string="Type computation mode"),
        'remind_update_delay': fields.integer('Remind delay',
            help="The number of days after which the user assigned to a manual goal will be reminded. Never reminded if no value is specified."),
        'last_update': fields.date('Last Update',
            help="In case of manual goal, reminders are sent if the goal as not been updated for a while (defined in goal plan). Ignored in case of non-manual goal or goal not linked to a plan."),

        'type_description': fields.related('type_id', 'description', type='char', string='Type Description', readonly=True),
        'type_suffix': fields.related('type_id', 'suffix', type='char', string='Type Description', readonly=True),
        'type_condition': fields.related('type_id', 'condition', type='char', string='Type Condition', readonly=True),
        'type_suffix': fields.related('type_id', 'full_suffix', type="char", string="Suffix", readonly=True),
        'type_display': fields.related('type_id', 'display_mode', type="char", string="Display Mode", readonly=True),
    }

    _defaults = {
        'current': 0,
        'state': 'draft',
        'start_date': fields.date.today,
    }
    _order = 'create_date desc, end_date desc, type_id, id'

    def _check_remind_delay(self, goal, context=None):
        """Verify if a goal has not been updated for some time and send a
        reminder message of needed.

        :return: data to write on the goal object
        """
        if goal.remind_update_delay and goal.last_update:
            delta_max = timedelta(days=goal.remind_update_delay)
            last_update = datetime.strptime(goal.last_update, DF).date()
            if date.today() - last_update > delta_max and goal.state == 'inprogress':
                # generate a remind report
                temp_obj = self.pool.get('email.template')
                template_id = self.pool['ir.model.data'].get_object(cr, uid, 'gamification', 'email_template_goal_reminder', context)
                body_html = temp_obj.render_template(cr, uid, template_id.body_html, 'gamification.goal', goal.id, context=context)

                self.message_post(cr, uid, goal.id, body=body_html, partner_ids=[goal.user_id.partner_id.id], context=context, subtype='mail.mt_comment')
                return {'state': 'inprogress_update'}
        return {}

    def update(self, cr, uid, ids, context=None):
        """Update the goals to recomputes values and change of states

        If a manual goal is not updated for enough time, the user will be
        reminded to do so (done only once, in 'inprogress' state).
        If a goal reaches the target value, the status is set to reached
        If the end date is passed (at least +1 day, time not considered) without
        the target value being reached, the goal is set as failed."""

        for goal in self.browse(cr, uid, ids, context=context):
            #TODO: towrite may be falsy, to avoid useless write on the object. Please check the whole thing is still working
            towrite = {}
            if goal.state in ('draft', 'canceled'):
                # skip if goal draft or canceled
                continue

            if goal.type_id.computation_mode == 'manually':
                towrite.update(self._check_remind_delay(goal, context))

            elif goal.type_id.computation_mode == 'python':
                # execute the chosen method
                values = {'cr': cr, 'uid': goal.user_id.id, 'context': context, 'self': self.pool.get('gamification.goal.type')}
                result = safe_eval(goal.type_id.compute_code, values, {})

                if type(result) in (float, int, long) and result != goal.current:
                    towrite['current'] = result
                else:
                    _logger.exception(_('Unvalid return content from the evaluation of %s' % str(goal.type_id.compute_code)))
                    # raise osv.except_osv(_('Error!'), _('Unvalid return content from the evaluation of %s' % str(goal.type_id.compute_code)))

            else:  # count or sum
                obj = self.pool.get(goal.type_id.model_id.model)
                field_date_name = goal.type_id.field_date_name
                # eval the domain with user_id replaced by goal user
                domain = safe_eval(goal.type_id.domain, {'user': goal.user_id})

                #add temporal clause(s) to the domain if fields are filled on the goal
                if goal.start_date and field_date_name:
                    domain.append((field_date_name, '>=', goal.start_date))
                if goal.end_date and field_date_name:
                    domain.append((field_date_name, '<=', goal.end_date))

                if goal.type_id.computation_mode == 'sum':
                    field_name = goal.type_id.field_id.name
                    rec_ids = obj.search(cr, uid, domain, context=context)
                    res = obj.read(cr, uid, rec_ids, [field_name], context=context)
                    new_value = res and res[0][field_name] or 0.0

                else:  # computation mode = count
                    new_value = obj.search(cr, uid, domain, context=context, count=True)

                #avoid useless write if the new value is the same as the old one
                if new_value != goal.current:
                    towrite['current'] = new_value

            # check goal target reached
            #TODO: reached condition is wrong because it should check time constraints.
            if (goal.type_id.condition == 'higher' and towrite.get('current', goal.current) >= goal.target_goal) or (goal.type_id.condition == 'lower' and towrite.get('current', goal.current) <= goal.target_goal):
                towrite['state'] = 'reached'

            # check goal failure
            elif goal.end_date and fields.date.today() > goal.end_date:
                towrite['state'] = 'failed'
            if towrite:
                self.write(cr, uid, [goal.id], towrite, context=context)
        return True

    def action_start(self, cr, uid, ids, context=None):
        """Mark a goal as started.

        This should only be used when creating goals manually (in draft state)"""
        self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)
        return self.update(cr, uid, ids, context=context)

    def action_reach(self, cr, uid, ids, context=None):
        """Mark a goal as reached.

        If the target goal condition is not met, the state will be reset to In
        Progress at the next goal update until the end date."""
        return self.write(cr, uid, ids, {'state': 'reached'}, context=context)

    def action_fail(self, cr, uid, ids, context=None):
        """Set the state of the goal to failed.

        A failed goal will be ignored in future checks."""
        return self.write(cr, uid, ids, {'state': 'failed'}, context=context)

    def action_cancel(self, cr, uid, ids, context=None):
        """Reset the completion after setting a goal as reached or failed.

        This is only the current state, if the date and/or target criterias
        match the conditions for a change of state, this will be applied at the
        next goal update."""
        return self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)

    def create(self, cr, uid, vals, context=None):
        """Overwrite the create method to add a 'no_remind_goal' field to True"""
        context = context or {}
        context['no_remind_goal'] = True
        return super(gamification_goal, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """Overwrite the write method to update the last_update field to today

        If the current value is changed and the report frequency is set to On
        change, a report is generated
        """
        vals['last_update'] = fields.date.today()
        result = super(gamification_goal, self).write(cr, uid, ids, vals, context=context)
        for goal in self.browse(cr, uid, ids, context=context):
            if goal.state != "draft" and ('type_id' in vals or 'user_id' in vals):
                # avoid drag&drop in kanban view
                raise osv.except_osv(_('Error!'), _('Can not modify the configuration of a started goal'))

            if vals.get('current'):
                if 'no_remind_goal' in context:
                    # new goals should not be reported
                    continue

                if goal.plan_id and goal.plan_id.report_message_frequency == 'onchange':
                    self.pool.get('gamification.goal.plan').report_progress(cr, SUPERUSER_ID, goal.plan_id, users=[goal.user_id], context=context)
        return result

    def get_action(self, cr, uid, goal_id, context=None):
        """Get the ir.action related to update the goal

        In case of a manual goal, should return a wizard to update the value
        :return: action description in a dictionnary
        """
        goal = self.browse(cr, uid, goal_id, context=context)
        if goal.type_id.action_id:
            #open a the action linked on the goal
            action = goal.type_id.action_id.read()[0]

            if goal.type_id.res_id_field:
                current_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                # this loop manages the cases where res_id_field is a browse record path (eg : company_id.currency_id.id)
                field_names = goal.type_id.res_id_field.split('.')
                res = current_user
                for field_name in field_names[:]:
                    res = res.__getitem__(field_name)
                action['res_id'] = res

                # if one element to display, should see it in form mode if possible
                views = action['views']
                for (view_id, mode) in action['views']:
                    if mode == "form":
                        views = [(view_id, mode)]
                        break
                action['views'] = views
            return action

        if goal.computation_mode == 'manually':
            #open a wizard window to update the value manually
            action = {
                'name': _("Update %s") % goal.type_id.name,
                'id': goal_id,
                'type': 'ir.actions.act_window',
                'views': [[False, 'form']],
                'target': 'new',
            }
            action['context'] = {'default_goal_id': goal_id, 'default_current': goal.current}
            action['res_model'] = 'gamification.goal.wizard'
            return action
        return False


class goal_manual_wizard(osv.TransientModel):
    """Wizard type to update a manual goal"""
    _name = 'gamification.goal.wizard'
    _columns = {
        'goal_id': fields.many2one("gamification.goal", string='Goal', required=True),
        'current': fields.float('Current'),
    }

    def action_update_current(self, cr, uid, ids, context=None):
        """Wizard action for updating the current value"""

        goal_obj = self.pool.get('gamification.goal')

        for wiz in self.browse(cr, uid, ids, context=context):
            towrite = {
                'current': wiz.current,
                'goal_id': wiz.goal_id.id,
            }
            goal_obj.write(cr, uid, [wiz.goal_id.id], towrite, context=context)
            goal_obj.update(cr, uid, [wiz.goal_id.id], context=context)
        return {}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
