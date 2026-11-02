<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <label class="budget-label" for="budget-slider">{{ t('restocking.budget') }}</label>
      <div class="budget-value">{{ money(budget, 0) }}</div>
      <input
        id="budget-slider"
        v-model.number="budget"
        type="range"
        min="0"
        max="5000"
        step="50"
        class="budget-slider"
        @input="scheduleLoad"
      />
      <div class="budget-scale">
        <span>{{ money(0, 0) }}</span>
        <span>{{ money(5000, 0) }}</span>
      </div>
    </div>

    <div v-if="loading && !result" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="result">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ money(result.budget, 0) }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="stat-value">{{ money(result.total_cost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div class="stat-value">{{ money(result.remaining_budget) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.longestLeadTime') }}</div>
          <div class="stat-value">{{ longestLeadTime }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ result.recommendations.length }})</h3>
          <button
            class="place-order-btn"
            :disabled="!result.recommendations.length || submitting || loading || planStale"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="submitError" class="error">{{ submitError }}</div>
        <div v-if="placedOrder" class="success-message">
          <div>
            {{ t('restocking.orderPlaced', { orderNumber: placedOrder.order_number }) }}
            {{ t('restocking.expectedDelivery') }}: {{ formatDate(placedOrder.expected_delivery) }}
          </div>
          <router-link to="/orders" class="orders-link">{{ t('restocking.viewOrders') }}</router-link>
        </div>

        <div v-if="!result.recommendations.length" class="empty-state">
          {{ t('restocking.empty') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.demandGap') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in result.recommendations" :key="rec.item_sku">
                <td><strong>{{ rec.item_sku }}</strong></td>
                <td>
                  {{ translateProductName(rec.item_name) }}
                  <span v-if="rec.partial" class="badge warning partial-badge">{{ t('restocking.partial') }}</span>
                </td>
                <td>
                  <span :class="['badge', rec.trend]">{{ trendLabel(rec.trend) }}</span>
                </td>
                <td class="num">{{ rec.demand_gap }}</td>
                <td class="num">{{ rec.quantity }}</td>
                <td class="num">{{ money(rec.unit_cost) }}</td>
                <td class="num"><strong>{{ money(rec.line_total) }}</strong></td>
                <td class="num">{{ rec.lead_time_days }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

    const budget = ref(2000)
    const result = ref(null)
    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitError = ref(null)
    const placedOrder = ref(null)
    // True between a slider move and the debounced fetch finishing, so the table
    // never gets submitted while it no longer matches the slider value.
    const planStale = ref(false)

    const money = (amount, decimals = 2) =>
      formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

    const trendLabel = (trend) => {
      const key = `trends.${trend}`
      const label = t(key)
      return label === key ? trend : label
    }

    const longestLeadTime = computed(() => {
      const recs = result.value?.recommendations || []
      if (!recs.length) return '-'
      return t('restocking.days', { count: Math.max(...recs.map(r => r.lead_time_days)) })
    })

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return '-'
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      })
    }

    // Monotonic request counter: while dragging, several requests can be in flight and
    // may resolve out of order. Only the latest request is allowed to update the state.
    let requestSeq = 0
    let debounceTimer = null

    const loadRecommendations = async () => {
      const seq = ++requestSeq
      planStale.value = false
      try {
        loading.value = true
        error.value = null
        const data = await api.getRestockingRecommendations(budget.value)
        if (seq !== requestSeq) return
        result.value = data
      } catch (err) {
        if (seq !== requestSeq) return
        error.value = t('restocking.loadError')
        console.error('Failed to load restocking recommendations:', err)
      } finally {
        if (seq === requestSeq) loading.value = false
      }
    }

    // Debounce: the slider fires `input` continuously while dragging, so wait for
    // ~250ms of inactivity before hitting the API. A previously placed order's
    // success message is cleared since it no longer matches the displayed plan.
    const scheduleLoad = () => {
      placedOrder.value = null
      submitError.value = null
      planStale.value = true
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(loadRecommendations, 250)
    }

    const placeOrder = async () => {
      if (!result.value || !result.value.recommendations.length || submitting.value) return
      try {
        submitting.value = true
        submitError.value = null
        placedOrder.value = null
        // Only sku + quantity are sent; the server sets prices and lead time.
        placedOrder.value = await api.createRestockingOrder({
          budget: result.value.budget,
          items: result.value.recommendations.map(r => ({
            item_sku: r.item_sku,
            quantity: r.quantity
          }))
        })
      } catch (err) {
        submitError.value = err.response?.data?.detail || t('restocking.orderError')
        console.error('Failed to place restocking order:', err)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)
    onBeforeUnmount(() => clearTimeout(debounceTimer))

    return {
      t, budget, result, loading, error, submitting, submitError, placedOrder, planStale,
      money, trendLabel, longestLeadTime, formatDate, scheduleLoad, placeOrder,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-label {
  font-size: 0.813rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.budget-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0.25rem 0 0.75rem;
}

.budget-slider {
  width: 100%;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.num {
  text-align: right;
}

.partial-badge {
  margin-left: 0.5rem;
  padding: 0.125rem 0.5rem;
  font-size: 0.688rem;
}

.place-order-btn {
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.success-message {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin: 0.75rem 1rem;
  font-size: 0.875rem;
}

.orders-link {
  color: #166534;
  font-weight: 600;
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: #64748b;
}
</style>
