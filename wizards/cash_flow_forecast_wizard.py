# -*- coding: utf-8 -*-
# Módulo proxit_cash_flow - Proxit
# Wizard de proyección de flujo de caja (esqueleto para Fase 2)

from odoo import models, fields


class ProxitCashFlowForecastWizard(models.TransientModel):
    _name = 'proxit.cash.flow.forecast.wizard'
    _description = 'Wizard de proyección de flujo de caja'

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company,
    )
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='Diarios',
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
        required=True,
    )
    date_as_of = fields.Date(
        string='Fecha base',
        required=True,
        default=fields.Date.today,
        help='Saldo inicial calculado a esta fecha.',
    )
    date_horizon = fields.Date(
        string='Fecha horizonte',
        required=True,
        help='Fecha límite de la proyección.',
    )
    include_draft_moves = fields.Boolean(
        string='Incluir asientos en borrador',
        default=False,
        help='Si se activa, se consideran también los asientos contables en estado borrador.',
    )

    def action_generate_forecast(self):
        """Genera la proyección de flujo de caja."""
        self.ensure_one()
        # TODO: Fase 2 - implementar motor de cálculo
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proyección de Flujo de Caja',
            'res_model': 'proxit.cash.flow.forecast.wizard',
            'view_mode': 'result',
            'target': 'new',
        }
