// U10 (DT-098): presupuesto de Cost Management a nivel de suscripción. Solo se despliega con
// deployBudget = true. Avisa; no detiene ni borra nada. Azure for Students no figura entre las ofertas que
// admite Cost Management, así que en esta suscripción se espera un rechazo (infra/azure/README.md).

targetScope = 'subscription'

param name string
param amount int
@description('Primer día del mes de inicio, AAAA-MM-01.')
param startDate string
param contactEmails array
param thresholds array

resource budget 'Microsoft.Consumption/budgets@2026-06-01' = {
  name: name
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    notifications: toObject(
      thresholds,
      threshold => 'actual-${threshold}',
      threshold => {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: threshold
        thresholdType: 'Actual'
        contactEmails: contactEmails
        contactRoles: [
          'Owner'
        ]
        locale: 'es-es'
      }
    )
  }
}
