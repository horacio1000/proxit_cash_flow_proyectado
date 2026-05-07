# -*- coding: utf-8 -*-
# Módulo proxit_cash_flow - Proxit
# Modelo transiente: línea individual del resultado de proyección

from odoo import models, fields


class ProxitCashFlowForecastLine(models.TransientModel):
    _name = 'proxit.cash.flow.forecast.line'
    _description = 'Línea de proyección de flujo de caja'
    _order = 'date, sequence'

    wizard_id = fields.Many2one(
        comodel_name='proxit.cash.flow.forecast.wizard',
        string='Wizard',
        ondelete='cascade',
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        index=True,
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
    )
    description = fields.Char(
        string='Concepto',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
    )
    amount = fields.Monetary(
        string='Importe',
        currency_field='currency_id',
    )
    balance = fields.Monetary(
        string='Saldo acumulado',
        currency_field='currency_id',
    )
    movement_type = fields.Selection(
        selection=[
            ('opening', 'Saldo inicial'),
            ('receivable', 'Cobro previsto'),
            ('payable', 'Pago previsto'),
            ('manual_income', 'Ingreso manual'),
            ('manual_expense', 'Egreso manual'),
        ],
        string='Origen',
    )
    reference = fields.Char(
        string='Referencia',
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
    )
