<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="report_cash_flow_forecast">
        <t t-call="web.html_container">
            <t t-foreach="docs" t-as="doc">
                <t t-call="web.internal_layout">
                    <div class="page">
                        <h2>Proyección de Flujo de Caja</h2>
                        <p><strong>Compañía:</strong> <t t-esc="doc.company_id.display_name"/></p>
                        <p><strong>Fecha base:</strong> <t t-esc="doc.date_as_of"/>
                        | <strong>Fecha horizonte:</strong> <t t-esc="doc.date_horizon"/>
                        <t t-if="doc.what_if_mode">
                            | <span class="text-warning"><strong>Modo what-if</strong></span>
                        </t>
                        </p>

                        <t t-if="doc.line_ids">
                            <table class="table table-condensed table-striped">
                                <thead>
                                    <tr>
                                        <th>Fecha</th>
                                        <th>Concepto</th>
                                        <th>Origen</th>
                                        <th class="text-right">Importe</th>
                                        <th class="text-right">Saldo</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <t t-foreach="doc.line_ids.sorted(key=lambda l: (l.date, l.sequence))" t-as="line">
                                        <tr>
                                            <td><t t-esc="line.date"/></td>
                                            <td><t t-esc="line.description"/></td>
                                            <td><t t-esc="dict(line._fields['movement_type'].selection).get(line.movement_type, line.movement_type)"/></td>
                                            <td class="text-right">
                                                <t t-if="line.amount >= 0">
                                                    <t t-esc="line.amount" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/>
                                                </t>
                                                <t t-else="">
                                                    <span class="text-danger"><t t-esc="-line.amount" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/></span>
                                                </t>
                                            </td>
                                            <td class="text-right">
                                                <t t-if="line.balance >= 0">
                                                    <t t-esc="line.balance" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/>
                                                </t>
                                                <t t-else="">
                                                    <span class="text-danger"><t t-esc="line.balance" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/></span>
                                                </t>
                                            </td>
                                        </tr>
                                    </t>
                                </tbody>
                            </table>

                            <div class="row mt16">
                                <div class="col-xs-4">
                                    <p><strong>Saldo inicial:</strong>
                                        <t t-esc="doc.line_ids[0].balance" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/>
                                    </p>
                                </div>
                                <div class="col-xs-4">
                                    <p><strong>Saldo mínimo:</strong>
                                        <t t-if="doc.has_negative_balance">
                                            <span class="text-danger">
                                                <t t-esc="doc.min_balance" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/>
                                            </span>
                                        </t>
                                        <t t-else="">
                                            <t t-esc="doc.min_balance" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/>
                                        </t>
                                    </p>
                                </div>
                                <div class="col-xs-4">
                                    <p><strong>Saldo final:</strong>
                                        <t t-if="doc.final_balance < 0">
                                            <span class="text-danger">
                                                <t t-esc="doc.final_balance" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/>
                                            </span>
                                        </t>
                                        <t t-else="">
                                            <t t-esc="doc.final_balance" t-options="{'widget': 'monetary', 'display_currency': doc.currency_id}"/>
                                        </t>
                                    </p>
                                </div>
                            </div>
                        </t>
                        <t t-if="not doc.line_ids">
                            <p class="text-muted">No hay datos de proyección. Calcule la proyección primero.</p>
                        </t>
                    </div>
                </t>
            </t>
        </t>
    </template>

    <record id="action_report_cash_flow_forecast" model="ir.actions.report">
        <field name="name">Proyección de Flujo de Caja</field>
        <field name="model">proxit.cash.flow.forecast.wizard</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">proxit_cash_flow.report_cash_flow_forecast</field>
        <field name="report_file">proxit_cash_flow.report_cash_flow_forecast</field>
        <field name="binding_model_id" ref="model_proxit_cash_flow_forecast_wizard"/>
        <field name="binding_type">report</field>
    </record>
</odoo>
