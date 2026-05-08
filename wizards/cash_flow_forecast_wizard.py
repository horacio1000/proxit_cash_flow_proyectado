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

    what_if_mode = fields.Boolean(
        string='Modo what-if',
        default=False,
        help='Permite ajustar fechas de cobros y pagos para simular escenarios.',
    )
    receivable_delay_days = fields.Integer(
        string='Retraso cobros (días)',
        default=0,
        help='Días adicionales para el vencimiento de las facturas de cliente.',
    )
    payable_delay_days = fields.Integer(
        string='Retraso pagos (días)',
        default=0,
        help='Días adicionales para el vencimiento de las facturas de proveedor.',
    )

    state = fields.Selection(
        selection=[('input', 'Parámetros'), ('result', 'Resultado')],
        default='input',
        string='Estado',
    )

    min_balance = fields.Monetary(
        string='Saldo mínimo proyectado',
        compute='_compute_kpis',
        currency_field='currency_id',
    )
    final_balance = fields.Monetary(
        string='Saldo final proyectado',
        compute='_compute_kpis',
        currency_field='currency_id',
    )
    has_negative_balance = fields.Boolean(
        string='¿Tiene saldo negativo?',
        compute='_compute_kpis',
    )
    initial_balance = fields.Monetary(
        string='Saldo inicial',
        compute='_compute_kpis',
        currency_field='currency_id',
    )
    total_income = fields.Monetary(
        string='Total ingresos',
        compute='_compute_kpis',
        currency_field='currency_id',
    )
    total_expense = fields.Monetary(
        string='Total egresos',
        compute='_compute_kpis',
        currency_field='currency_id',
    )
    income_count = fields.Integer(
        string='Cantidad de ingresos',
        compute='_compute_kpis',
    )
    expense_count = fields.Integer(
        string='Cantidad de egresos',
        compute='_compute_kpis',
    )
    negative_days = fields.Integer(
        string='Días con saldo negativo',
        compute='_compute_kpis',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        related='company_id.currency_id',
        readonly=True,
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

    def _get_liquidity_journals(self):
        return self.env['account.journal'].search([
            ('type', 'in', ('bank', 'cash', 'credit')),
            ('company_id', '=', self.company_id.id),
        ])

    def action_generate_forecast(self):
        self.ensure_one()
        self.line_ids.unlink()

        if self.date_horizon < self.date_as_of:
            raise UserError(_('La fecha horizonte debe ser posterior o igual a la fecha base.'))

        lines_vals = self._compute_forecast()
        commands = [(0, 0, vals) for vals in lines_vals]
        self.line_ids = commands
        self.state = 'result'

        return {
            'type': 'ir.actions.act_window',
            'name': 'Proyección de Flujo de Caja',
            'res_model': 'proxit.cash.flow.forecast.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'create': False, 'delete': False},
        }

    def action_back_to_input(self):
        self.state = 'input'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Proyección de Flujo de Caja',
            'res_model': 'proxit.cash.flow.forecast.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'create': False, 'delete': False},
        }

    def action_open_graph(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Gráfico de Flujo de Caja',
            'res_model': 'proxit.cash.flow.forecast.line',
            'view_mode': 'graph',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'new',
            'context': {'create': False, 'delete': False},
        }

    def action_open_pivot(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tabla dinámica de Flujo de Caja',
            'res_model': 'proxit.cash.flow.forecast.line',
            'view_mode': 'pivot',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'new',
            'context': {'create': False, 'delete': False},
        }

    def _compute_kpis(self):
        """Calcula todos los KPI del dashboard."""
        for wizard in self:
            lines = wizard.line_ids
            if not lines:
                wizard.min_balance = 0
                wizard.final_balance = 0
                wizard.has_negative_balance = False
                wizard.initial_balance = 0
                wizard.total_income = 0
                wizard.total_expense = 0
                wizard.income_count = 0
                wizard.expense_count = 0
                wizard.negative_days = 0
                continue

            opening = lines.filtered(lambda l: l.movement_type == 'opening')
            wizard.initial_balance = opening[0].amount if opening else 0

            income_lines = lines.filtered(lambda l: l.amount > 0 and l.movement_type != 'opening')
            expense_lines = lines.filtered(lambda l: l.amount < 0 and l.movement_type != 'opening')

            wizard.total_income = sum(income_lines.mapped('amount'))
            wizard.total_expense = sum(expense_lines.mapped('amount'))
            wizard.income_count = len(income_lines)
            wizard.expense_count = len(expense_lines)

            wizard.min_balance = min(lines.mapped('balance'))
            wizard.has_negative_balance = wizard.min_balance < 0

            last_line = lines.sorted(key=lambda l: (l.date, l.sequence), reverse=True)
            wizard.final_balance = last_line[0].balance if last_line else 0

            neg_dates = set()
            for line in lines:
                if line.balance < 0:
                    neg_dates.add(line.date)
            wizard.negative_days = len(neg_dates)

    def _apply_what_if(self, movements):
        """Ajusta fechas de movimientos según modo what-if."""
        if not self.what_if_mode:
            return movements
        delay_map = {'receivable': self.receivable_delay_days, 'payable': self.payable_delay_days}
        import datetime
        for m in movements:
            delay = delay_map.get(m['movement_type'], 0)
            if delay:
                from datetime import timedelta
                m['date'] = m['date'] + timedelta(days=delay)
        return movements

    def _compute_forecast(self):
        """Retorna la lista de dicts para crear las líneas de proyección."""
        self.ensure_one()
        movements = []

        # 1. Saldo base por diario (siempre se muestra, aunque sea 0)
        base_by_journal = self._get_base_balance()
        total_base = sum(base_by_journal.values())
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

        # 5. Cheques de terceros pendientes de depósito (futuros ingresos)
        movements += self._get_third_party_check_moves()

        # 6. Cheques propios pendientes de débito (futuros egresos)
        movements += self._get_own_check_moves()

        # 7. Aplicar modo what-if
        movements = self._apply_what_if(movements)

        # 8. Ordenar por fecha y secuencia, luego acumular saldo
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

        journals = self._get_liquidity_journals()
        if not journals:
            return {}

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

        self.env.cr.execute(query, [self.date_as_of, tuple(journals.ids), self.company_id.id])
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
        journals = self._get_liquidity_journals()
        lines = self.env['proxit.cash.flow.manual.line'].search([
            ('state', '=', 'confirmed'),
            ('date_expected', '>=', self.date_as_of),
            ('date_expected', '<=', self.date_horizon),
            ('company_id', '=', self.company_id.id),
            ('journal_id', 'in', journals.ids),
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

    # -----------------------------------------------------------------
    # CHEQUES DE TERCEROS (futuros ingresos)
    # -----------------------------------------------------------------

    def _get_third_party_check_moves(self):
        """Retorna movimientos de cheques de terceros pendientes de depósito."""
        self.ensure_one()
        try:
            Check = self.env['l10n_latam.check']
        except KeyError:
            return []
        checks = Check.search([
            ('payment_method_code', '=', 'new_third_party_checks'),
            ('payment_id.state', 'not in', ['draft', 'canceled', 'rejected']),
            ('payment_date', '>=', self.date_as_of),
            ('payment_date', '<=', self.date_horizon),
            ('company_id', '=', self.company_id.id),
            ('current_journal_id.inbound_payment_method_line_ids.payment_method_id.code', '=', 'in_third_party_checks'),
        ])
        return [{
            'date': check.payment_date,
            'sequence': 8,
            'description': 'Cheque tercero - %s' % (check.partner_id.display_name or ''),
            'partner_id': check.partner_id.id,
            'reference': check.name,
            'amount': check.amount,
            'balance': 0,
            'movement_type': 'third_party_check',
            'journal_id': check.current_journal_id.id,
            'company_id': check.company_id.id,
        } for check in checks if check.amount]

    # -----------------------------------------------------------------
    # CHEQUES PROPIOS (futuros egresos)
    # -----------------------------------------------------------------

    def _get_own_check_moves(self):
        """Retorna movimientos de cheques propios pendientes de débito."""
        self.ensure_one()
        try:
            Check = self.env['l10n_latam.check']
        except KeyError:
            return []
        checks = Check.search([
            ('payment_method_code', '=', 'own_checks'),
            ('payment_id.state', 'not in', ['draft', 'canceled', 'rejected']),
            ('issue_state', '=', 'handed'),
            ('payment_date', '>=', self.date_as_of),
            ('payment_date', '<=', self.date_horizon),
            ('company_id', '=', self.company_id.id),
        ])
        return [{
            'date': check.payment_date,
            'sequence': 8,
            'description': 'Cheque propio - %s' % (check.partner_id.display_name or ''),
            'partner_id': check.partner_id.id,
            'reference': check.name,
            'amount': -check.amount,
            'balance': 0,
            'movement_type': 'own_check',
            'journal_id': check.original_journal_id.id,
            'company_id': check.company_id.id,
        } for check in checks if check.amount]
