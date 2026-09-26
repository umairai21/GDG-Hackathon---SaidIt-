async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = new Error(`${res.status} ${await res.text()}`)
    err.status = res.status // 401 = store manager not signed in
    throw err
  }
  return res.json()
}

const post = (path, body) => request(path, { method: 'POST', body: body && JSON.stringify(body) })

export const api = {
  search: (query) => post('/search', { query }),
  click: (query, productId) => post('/feedback', { query, product_id: productId, type: 'click' }),
  notWhatIMeant: (query) => post('/feedback', { query, product_id: null, type: 'not_what_i_meant' }),
  // store manager only (the server checks the session cookie)
  login: (password) => post('/auth/login', { password }),
  logout: () => post('/auth/logout'),
  me: () => request('/auth/me'),
  words: () => request('/store/words'),
  changelog: () => request('/store/changelog'),
  approve: (id) => post(`/store/mappings/${id}/approve`),
  remove: (id) => post(`/store/mappings/${id}/remove`),
  evalSummary: () => request('/eval/summary'),
}
