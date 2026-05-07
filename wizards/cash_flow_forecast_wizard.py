# -*- coding: utf-8 -*-
# Módulo proxit_cash_flow - Proxit
# Wizard de proyección de flujo de caja con motor de cálculo

from collections import defaultdict
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
        help='Saldo inicial calculado a partir de asientos contabilizados hasta esta fecha.',
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

    line_ids = fields.One2many(
        comodel_name='proxit.cash.flow.forecast.line',
        inverse_name='wizard_id',
        string='Líneas proyectadas',
        readonly=True,
    )

    # -----------------------------------------------------------------
    # CÁLCULO PRINCIPAL
    # -----------------------------------------------------------------

    def action_generate_forecast(self):
        self.ensure_one()
        self.line_ids.unlink()

        if not self.journal_ids:
            raise UserError(_('Debe seleccionar al menos un diario.'))

        if self.date_horizon < self.date_as_of:
            raise UserError(_('La fecha horizonte debe ser posterior o igual a la fecha base.'))

        lines_vals = self._compute_forecast()
        self.line_ids = lines_vals

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'proxit.cash.flow.forecast.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def _compute_forecast(self):
        """Retorna la lista de dicts para crear las líneas de proyección."""
        self.ensure_one()
        movements = []

        # 1. Saldo base por diario
        base_by_journal = self._get_base_balance()
        total_base = sum(base_by_journal.values())
        if total_base:
            movements.append({
                'date': self.date_as_of,
                'sequence': 0,
                'description': 'Saldo inicial',
                'amount': total_base,
                'balance': total_base,
                'movement_type': 'opening',
                'company_id': self.company_id.id,
            })

        # 2. Facturas de cliente pendientes (cobros)
        movements += self._get_receivable_moves()

        # 3. Facturas de proveedor pendientes (pagos)
        movements += self._get_payable_moves()

        # 4. Líneas manuales confirmadas
        movements += self._get_manual_moves()

        # 5. Ordenar por fecha y secuencia, luego acumular saldo
        movements.sort(key=lambda m: (m['date'], m['sequence']))
        running = total_base
        for move in movements:
            if move['movement_type'] != 'opening':
                running += move['amount']
                move['balance'] = running

        return movements

    # -----------------------------------------------------------------
    # SALDO BASE (SQL)
    # -----------------------------------------------------------------

    def _get_base_balance(self):
        """Retorna {journal_id: saldo} con la suma de move_lines en cuentas de liquidez."""
        self.ensure_one()
        state_filter = "'posted'"
        if self.include_draft_moves:
            state_filter = "'posted', 'draft'"

        query = """
            SELECT aml.journal_id, COALESCE(SUM(aml.balance), 0.0) AS balance
            FROM account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN account_move am ON am.id = aml.move_id
            WHERE aa.account_type IN ('asset_cash', 'liability_credit_card')
              AND am.state IN (%s)
              AND aml.date <= %%s
              AND aml.journal_id IN %%s
              AND aml.company_id = %%s
            GROUP BY aml.journal_id
        """ % state_filter

        self.env.cr.execute(query, [self.date_as_of, tuple(self.journal_ids.ids), self.company_id.id])
        rows = self.env.cr.dictfetchall()
        return {r['journal_id']: r['balance'] for r in rows}

    # -----------------------------------------------------------------
    # CUENTAS A COBRAR (SQL)
    # -----------------------------------------------------------------

    def _get_receivable_moves(self):
        """Retorna movimientos de cobros futuros desde líneas payment_term no reconciliadas."""
        self.ensure_one()
        query = """
            SELECT
                aml.date_maturity AS date,
                am.name AS ref,
                am.partner_id,
                aml.journal_id,
                aml.amount_residual AS amount
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aml.display_type = 'payment_term'
              AND aml.reconciled = FALSE
              AND am.state = 'posted'
              AND aa.account_type = 'asset_receivable'
              AND am.move_type IN ('out_invoice', 'out_refund')
              AND aml.date_maturity BETWEEN %s AND %s
              AND aml.company_id = %s
            ORDER BY aml.date_maturity
        """
        self.env.cr.execute(query, [self.date_as_of, self.date_horizon, self.company_id.id])
        rows = self.env.cr.dictfetchall()
        return [{
            'date': r['date'],
            'sequence': 5,
            'description': 'Cobro previsto',
            'partner_id': r['partner_id'],
            'reference': r['ref'],
            'amount': r['amount'],
            'balance': 0,
            'movement_type': 'receivable',
            'journal_id': r['journal_id'],
            'company_id': self.company_id.id,
        } for r in rows if r['amount']]

    # -----------------------------------------------------------------
    # CUENTAS A PAGAR (SQL)
    # -----------------------------------------------------------------

    def _get_payable_moves(self):
        """Retorna movimientos de pagos futuros desde líneas payment_term no reconciliadas."""
        self.ensure_one()
        query = """
            SELECT
                aml.date_maturity AS date,
                am.name AS ref,
                am.partner_id,
                aml.journal_id,
                aml.amount_residual AS amount
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
            WHERE aml.display_type = 'payment_term'
              AND aml.reconciled = FALSE
              AND am.state = 'posted'
              AND aa.account_type = 'liability_payable'
              AND am.move_type IN ('in_invoice', 'in_refund')
              AND aml.date_maturity BETWEEN %s AND %s
              AND aml.company_id = %s
            ORDER BY aml.date_maturity
        """
        self.env.cr.execute(query, [self.date_as_of, self.date_horizon, self.company_id.id])
        rows = self.env.cr.dictfetchall()
        return [{
            'date': r['date'],
            'sequence': 5,
            'description': 'Pago previsto',
            'partner_id': r['partner_id'],
            'reference': r['ref'],
            'amount': r['amount'],  # amount_residual en payable es negativo → egreso
            'balance': 0,
            'movement_type': 'payable',
            'journal_id': r['journal_id'],
            'company_id': self.company_id.id,
        } for r in rows if r['amount']]

    # -----------------------------------------------------------------
    # LÍNEAS MANUALES (ORM)
    # -----------------------------------------------------------------

    def _get_manual_moves(self):
        """Retorna movimientos desde líneas manuales confirmadas."""
        self.ensure_one()
        lines = self.env['proxit.cash.flow.manual.line'].search([
            ('state', '=', 'confirmed'),
            ('date_expected', '>=', self.date_as_of),
            ('date_expected', '<=', self.date_horizon),
            ('company_id', '=', self.company_id.id),
            ('journal_id', 'in', self.journal_ids.ids),
        ])
        return [{
            'date': line.date_expected,
            'sequence': 15,
            'description': line.name,
            'partner_id': False,
            'reference': False,
            'amount': line.amount if line.movement_type == 'income' else -line.amount,
            'balance': 0,
            'movement_type': 'manual_income' if line.movement_type == 'income' else 'manual_expense',
            'journal_id': line.journal_id.id,
            'company_id': line.company_id.id,
        } for line in lines]
