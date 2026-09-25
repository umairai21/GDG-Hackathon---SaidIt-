async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}

const post = (path, body) => request(path, { method: 'POST', body: body && JSON.stringify(body) })

export const api = {
  search: (query) => post('/search', { query }),
  click: (query, productId) => post('/feedback', { query, product_id: productId, type: 'click' }),
  notWhatIMeant: (query) => post('/feedback', { query, product_id: null, type: 'not_what_i_meant' }),
  words: () => request('/store/words'),
  changelog: () => request('/store/changelog'),
  approve: (id) => post(`/store/mappings/${id}/approve`),
  remove: (id) => post(`/store/mappings/${id}/remove`),
  evalSummary: () => request('/eval/summary'),
}
