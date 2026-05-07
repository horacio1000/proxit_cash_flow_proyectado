# -*- coding: utf-8 -*-
# Módulo proxit_cash_flow - Proxit
# Modelo: Línea manual de flujo de caja

from odoo import models, fields, api


class ProxitCashFlowManualLine(models.Model):
    _name = 'proxit.cash.flow.manual.line'
    _description = 'Línea manual de flujo de caja'
    _order = 'date_expected, id'
    _check_company_auto = True

    name = fields.Char(
        string='Descripción',
        required=True,
    )
    date_expected = fields.Date(
        string='Fecha esperada',
        required=True,
        default=fields.Date.today,
        index=True,
        help='Fecha en la que se espera que ocurra este movimiento.',
    )
    amount = fields.Monetary(
        string='Importe',
        required=True,
        currency_field='currency_id',
        help='Importe del movimiento. Usar valor positivo para ingreso y negativo para egreso.',
    )
    movement_type = fields.Selection(
        selection=[
            ('income', 'Ingreso'),
            ('expense', 'Egreso'),
        ],
        string='Tipo',
        required=True,
        default='income',
    )
    notes = fields.Text(
        string='Notas',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('done', 'Realizado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        required=True,
        default='draft',
        index=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario',
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
        check_company=True,
        help='Diario bancario, de caja o tarjeta de crédito asociado.',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
    )

    def action_confirm(self):
        self.state = 'confirmed'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'
