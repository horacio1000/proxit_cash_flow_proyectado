{
    'name': 'Proxit Flujo de Caja',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Cash Flow',
    'summary': 'Proyección de flujo de caja con movimientos manuales, facturas pendientes y cheques.',
    'description': """
Módulo de proyección de flujo de caja para Odoo 19.

Permite visualizar el saldo proyectado considerando:
- Saldo actual en diarios bancarios, de caja y tarjeta de crédito
- Facturas de cliente pendientes de cobro
- Facturas de proveedor pendientes de pago
- Fechas de vencimiento y condiciones de pago
- Movimientos manuales proyectados (ingresos/egresos aún no contabilizados)
- Cheques de terceros y propios (con integración l10n_latam_check)

Todas las etiquetas y documentación están en español.
    """,
    'author': 'Proxit',
    'license': 'LGPL-3',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/cash_flow_manual_line_views.xml',
        'views/cash_flow_forecast_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
